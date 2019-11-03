"""
pymd2re.py
  Convert Markdown file to Re:VIEW file.
"""


import argparse
from enum import IntEnum, auto
import re


DEBUG_MODE = True


class Inline:
    '''
    インラインクラス
    '''

    class Kind(IntEnum):
        '''
        種別
        '''
        PLANE = auto()          # プレーンテキスト
        COMMENT = auto()        # コメント
        BOLD = auto()           # ボールド
        ITALIC = auto()         # イタリック
        BOLD_ITALIC = auto()    # ボールド＆イタリック
        CODE = auto()           # コード
        STRIKE = auto()         # 取消線
        EMOJI = auto()          # 絵文字
        LINK = auto()           # リンク
        IMAGE = auto()          # 画像

    def __init__(self, kind=Kind.PLANE):
        '''
        コンストラクタ
        '''
        # 種別
        self.kind = kind
        # 文字列
        self.texts = []

    def __str__(self):
        '''
        テキスト化
        '''
        output = '[I:' + self.kind.name + ']'
        for text in self.texts:
            text = text.replace('\n', r'\n')
            text = text.replace('\t', r'\t')
            output += ' ("' + text + '")'

        return output

class Block:
    '''
    ブロッククラス
    '''

    class Kind(IntEnum):
        '''
        種別
        '''
        DOCUMENT = auto()       # 文書全体
        COMMENT = auto()        # コメント
        HEADER = auto()         # 見出し
        HR = auto()             # 水平線
        IMAGE = auto()          # 画像
        PRE = auto()            # 整形済みテキスト
        CODE = auto()           # コード
        QUOTE = auto()          # 引用
        TABLE = auto()          # 表
        LIST = auto()           # リスト
        LIST_ORDERED = auto()   # 番号付きリスト
        LIST_CHECK = auto()     # チェックリスト
        PARA = auto()           # 段落

    def __init__(self, kind=Kind.DOCUMENT, parent=None):
        '''
        コンストラクタ
        '''
        # 種別
        self.kind = kind
        # サブコンテンツ
        self.subitems = []
        # 親コンテンツ
        self.parent = parent
        # レベル
        self.level = 0     # ヘッダ、リストで使用する

    def __str__(self):
        '''
        テキスト化
        '''
        output = '[B:' + self.kind.name + ']'
        if self.level > 0:
            output += ' lv=' + str(self.level)

        return output


class MarkdownParser:
    '''
    Markdownパーサー
    '''

    def __init__(self):
        '''
        コンストラクタ
        '''
        # ブロックのための正規表現オブジェクト
        # リストに内包可能なものは先頭のインデントを許容（\s*）
        self._regexb = {}
        self._regexb[Block.Kind.COMMENT] = []                                                   # コメント
        self._regexb[Block.Kind.COMMENT].append(re.compile(r'^<!-{2,}(.*?)(-{2,}>)?$'))         #   [0] 開始 ※同じ行で終了する場合を考慮
        self._regexb[Block.Kind.COMMENT].append(re.compile(r'^(.*?)-{2,}>'))                    #   [1] 終了
        self._regexb[Block.Kind.HEADER] = []                                                    # 見出し
        self._regexb[Block.Kind.HEADER].append(re.compile(r'^(#+) (.*)'))                       #   [0] 行頭が #
        self._regexb[Block.Kind.HEADER].append(re.compile(r'^(={3,}|-{3,})$'))                  #   [1] 次行が === ---
        self._regexb[Block.Kind.HR] = re.compile(r'^(\*{3,}|-{3,}|_{3,})$')                     # 水平線
        self._regexb[Block.Kind.IMAGE] = re.compile(r'^\s*!\[(.+?)\]\((.+?)( +"(.+?)")?\)$')    # 画像
        self._regexb[Block.Kind.PRE] = re.compile(r'^ {4}(.*)$')                                # 整形済みテキスト
        self._regexb[Block.Kind.CODE] = re.compile(r'^\s*`{3}(.*)$')                            # コード
        self._regexb[Block.Kind.QUOTE] = re.compile(r'^\s*(>+)(.*)$')                           # 引用
        self._regexb[Block.Kind.TABLE] = []                                                     # 表
        self._regexb[Block.Kind.TABLE].append(re.compile(r'^\s*(\|\s*[^\|]*?\s*)+\|$'))         #   [0] データ行
        self._regexb[Block.Kind.TABLE].append(re.compile(r'^\s*(\|\s*-+?\s*)+\|$'))             #   [1] 区切り行
        self._regexb[Block.Kind.LIST] = re.compile(r'^(-|\*) (.*)$')                            # リスト
        self._regexb[Block.Kind.LIST_ORDERED] = re.compile(r'^(\d+\.) (.*)$')                   # 番号付きリスト
        self._regexb[Block.Kind.LIST_CHECK] = re.compile(r'^(-|\*) \[( |x|X)?\] (.*)$')         # チェックリスト
        self._regexb[Block.Kind.PARA] = re.compile(r'^\s*(.+)$')                                # 段落

        # インラインのための正規表現
        restr = {}
        restr[Inline.Kind.COMMENT] = r'<!-{2,}([^-]*?)-{2,}>'                       # <!--xxx-->
        restr[Inline.Kind.BOLD] = r'\*{1}([^\*]+?)\*{1}|_{1}([^_]+?)_{1}'           # *xxx* or _xxx_
        restr[Inline.Kind.ITALIC] = r'\*{2}([^\*]+?)\*{2}|_{2}([^_]+?)_{1}'         # **xxx** or __xxx__
        restr[Inline.Kind.BOLD_ITALIC] = r'\*{3}([^\*]+?)\*{3}|_{3}([^_]+?)_{3}'    # ***xxx*** or ___xxx___
        restr[Inline.Kind.CODE] = r'`(.+?)`'                                        # `xxx`
        restr[Inline.Kind.STRIKE] = r'~{2}(.+?)~{2}'                                # ~~xxx~~
        restr[Inline.Kind.EMOJI] = r'\:(.+?)\:'                                     # :xxx:
        url = r'http(s)?://([-\w]+\.)+[-\w]+(/[-./?%&=\w]*)?'
        restr[Inline.Kind.LINK] = r'\[(.+?)\]\((.+?)\)' + '|' + '(' + url + ')'     # [xxx](yyy) or http:...
        restr[Inline.Kind.IMAGE] = r'!\[(.+?)\]\((.+?)( +"(.+?)" *)?\)'             # ![xxx](yyy "zzz")

        # インラインのための正規表現中の、保持する可能性のあるテキストを表すグループ番号
        self._regext_gid = {}
        self._regext_gid[Inline.Kind.COMMENT] = (1,)        # コメント
        self._regext_gid[Inline.Kind.BOLD] = (1, 2)         # ボールド
        self._regext_gid[Inline.Kind.ITALIC] = (1, 2)       # イタリック
        self._regext_gid[Inline.Kind.BOLD_ITALIC] = (1, 2)  # ボールド＆イタリック
        self._regext_gid[Inline.Kind.CODE] = (1,)           # コード
        self._regext_gid[Inline.Kind.STRIKE] = (1,)         # 取消線
        self._regext_gid[Inline.Kind.EMOJI] = (1,)          # 絵文字
        self._regext_gid[Inline.Kind.LINK] = (1, 2, 3)      # リンク
        self._regext_gid[Inline.Kind.IMAGE] = (1, 2, 4)     # 画像

        # インラインのための正規表現オブジェクト
        self._regext = {}
        self._regext[Inline.Kind.COMMENT] = re.compile(restr[Inline.Kind.COMMENT])          # コメント
        self._regext[Inline.Kind.BOLD] = re.compile(restr[Inline.Kind.BOLD])                # ボールド
        self._regext[Inline.Kind.ITALIC] = re.compile(restr[Inline.Kind.ITALIC])            # イタリック
        self._regext[Inline.Kind.BOLD_ITALIC] = re.compile(restr[Inline.Kind.BOLD_ITALIC])  # ボールド＆イタリック
        self._regext[Inline.Kind.CODE] = re.compile(restr[Inline.Kind.CODE])                # コード
        self._regext[Inline.Kind.STRIKE] = re.compile(restr[Inline.Kind.STRIKE])            # 取消線
        self._regext[Inline.Kind.EMOJI] = re.compile(restr[Inline.Kind.EMOJI])              # 絵文字
        self._regext[Inline.Kind.LINK] = re.compile(restr[Inline.Kind.LINK])                # リンク
        self._regext[Inline.Kind.IMAGE] = re.compile(restr[Inline.Kind.IMAGE])              # 画像
        # インライン分割用の正規表現オブジェクト
        self._regext_all = re.compile('|'.join(restr.values()))

    def __call__(self, lines):
        '''
        ()演算子：パース処理
        '''
        doc = Block()

        # スキップのためのインデックス：スキップなし
        skip = -1

        # 全行ループ
        for i, cur_line in enumerate(lines):
            # 直前の処理でループを進めている場合はその位置までスキップ
            if i <= skip: continue

            # 空行
            if len(cur_line) == 0: continue

            # コメント
            done, skip = self._parse_block_comment(doc, lines, i)
            if done: continue

            # 見出し(行頭が # のケース)
            done, skip = self._parse_block_header_single(doc, lines, i)
            if done: continue

            # 水平線
            done, skip = self._parse_block_hr(doc, lines, i)
            if done: continue

            # 画像
            done, skip = self._parse_block_image(doc, lines, i)
            if done: continue

            # 整形済みテキスト
            done, skip = self._parse_block_pre(doc, lines, i)
            if done: continue

            # コード
            done, skip = self._parse_block_code(doc, lines, i)
            if done: continue

            # 引用
            done, skip = self._parse_block_quote(doc, lines, i)
            if done: continue

            # 表
            done, skip = self._parse_block_table(doc, lines, i)
            if done: continue

            # リスト
            done, skip = self._parse_block_list(doc, lines, i)
            if done: continue

            # 見出し(次行が === --- のケース)
            done, skip = self._parse_block_header_multiple(doc, lines, i)
            if done: continue

            # 段落
            done, skip = self._parse_block_para(doc, lines, i)
            if done: continue

        return doc

    def _parse_block_comment(self, cur_block, lines, i):
        '''
        ブロック：コメントを解析
        '''
        done = False
        skip = i

        match = self._regexb[Block.Kind.COMMENT][0].match(lines[i])
        if match:
            sub_lines = []
            # コメント開始直後の文字列をコメントとして退避
            sub_lines.append(match[1])

            # 同じ行でコメントが終了してない場合
            if match.lastindex < 2:
                # 次の行からループを進める
                if i < len(lines) - 1:
                    for j, sub_line in enumerate(lines[i+1:]):
                        # コメント終了を見つけたらループ終了
                        match = self._regexb[Block.Kind.COMMENT][1].match(sub_line)
                        if match:
                            sub_lines.append(match[1])
                            # ループを進めた位置までスキップさせる
                            skip = (i + 1) + j
                            break
                        # 途中の文字列は退避
                        sub_lines.append(lines[(i + 1) + j])
                    else:
                        # 最後までスキップ
                        skip = len(lines)

            # ブロック作成
            block = Block(Block.Kind.COMMENT, cur_block)
            # 情報を格納
            inline = Inline()
            inline.texts.append('\n'.join(sub_lines))
            block.subitems.append(inline)
            # カレントブロックに登録
            cur_block.subitems.append(block)
            done = True

        return done, skip

    def _parse_block_header_single(self, cur_block, lines, i):
        '''
        ブロック：見出し(行頭が # のケース)を解析
        '''
        done = False
        skip = i

        match = self._regexb[Block.Kind.HEADER][0].match(lines[i])
        if match:
            # ブロック作成
            block = Block(Block.Kind.HEADER, cur_block)
            # 情報を格納
            block.level = match[1].count('#')
            inlines = self._parse_inline(match[2])
            block.subitems.extend(inlines)
            # カレントブロックに登録
            cur_block.subitems.append(block)
            done = True

        return done, skip

    def _parse_block_header_multiple(self, cur_block, lines, i):
        '''
        ブロック：見出し(次行が === --- のケース)を解析
        '''
        done = False
        skip = i

        if i < len(lines) - 1:
            # 次行をチェック
            sub_line = lines[i+1]
            match = self._regexb[Block.Kind.HEADER][1].match(sub_line)
            if match:
                # ブロック作成
                block = Block(Block.Kind.HEADER, cur_block)
                # 情報を格納
                block.level = 1 if '=' in sub_line else 2
                inlines = self._parse_inline(lines[i])
                block.subitems.extend(inlines)
                # カレントブロックに登録
                cur_block.subitems.append(block)
                skip = i + 1
                done = True

        return done, skip

    def _parse_block_hr(self, cur_block, lines, i):
        '''
        ブロック：水平線を解析
        '''
        done = False
        skip = i

        match = self._regexb[Block.Kind.HR].match(lines[i])
        if match:
            # ブロック作成
            block = Block(Block.Kind.HR, cur_block)
            # カレントブロックに登録
            cur_block.subitems.append(block)
            done = True

        return done, skip

    def _parse_block_image(self, cur_block, lines, i):
        '''
        ブロック：画像を解析
        '''
        done = False
        skip = i

        match = self._regexb[Block.Kind.IMAGE].match(lines[i])
        if match:
            # ブロック作成
            block = Block(Block.Kind.IMAGE, cur_block)
            # 情報を格納
            inlines = self._parse_inline(match[0])
            block.subitems.extend(inlines)
            # カレントブロックに登録
            cur_block.subitems.append(block)
            done = True

        return done, skip

    def _parse_block_pre(self, cur_block, lines, i):
        '''
        ブロック：整形済みテキストを解析
        '''
        done = False
        skip = i

        match = self._regexb[Block.Kind.PRE].match(lines[i])
        if match:
            sub_lines = []

            # 現在行からループを進める
            for j, sub_line in enumerate(lines[i:]):
                # マッチしなくなったらループ終了
                match = self._regexb[Block.Kind.PRE].match(sub_line)
                if not match:
                    # ループを進めた位置の直前までスキップさせる
                    skip = i + j - 1
                    break
                # 途中の文字列は退避
                sub_lines.append(lines[i])
            else:
                # 最後までスキップ
                skip = len(lines)

            # ブロック作成
            block = Block(Block.Kind.PRE, cur_block)
            # 情報を格納
            inline = '\n'.join(sub_lines)
            block.subitems.append(inline)
            # カレントブロックに登録
            cur_block.subitems.append(block)
            done = True

        return done, skip

    def _parse_block_code(self, cur_block, lines, i):
        '''
        ブロック：コードを解析
        '''
        done = False
        skip = i

        match = self._regexb[Block.Kind.CODE].match(lines[i])
        if match:
            sub_lines = []

            # 次の行からループを進める
            if i < len(lines) - 1:
                for j, sub_line in enumerate(lines[i+1:]):
                    # ブロック終了を見つけたらループ終了
                    match = self._regexb[Block.Kind.CODE].match(sub_line)
                    if match:
                        # ループを進めた位置までスキップさせる
                        skip = (i + 1) + j
                        break
                    # 途中の文字列はコードとして退避
                    sub_lines.append(lines[i])
                else:
                    # 最後までスキップ
                    skip = len(lines)

            # ブロック作成
            block = Block(Block.Kind.CODE, cur_block)
            # 情報を格納
            inline = '\n'.join(sub_lines)
            block.subitems.append(inline)
            # カレントブロックに登録
            cur_block.subitems.append(block)
            done = True

        return done, skip

    def _parse_block_quote(self, cur_block, lines, i):
        '''
        ブロック：引用を解析
        '''
        done = False
        skip = i

        match = self._regexb[Block.Kind.QUOTE].match(lines[i])
        if match:
            cur_level = 0

            # 現在行からループを進める
            for j, sub_line in enumerate(lines[i:]):
                # マッチしなくなったらループ終了
                match = self._regexb[Block.Kind.QUOTE].match(sub_line)
                if not match:
                    # ループを進めた位置の直前までスキップさせる
                    skip = i + j - 1
                    break

                # 深さ
                level = match[1].count('>')

                # 深さが減少した場合
                if level < cur_level:
                    # カレントブロックを上へ移動
                    for _ in range(cur_level - level):
                        cur_block = cur_block.parent

                # 深さが同じ場合
                elif level == cur_level:
                    # ブロックはそのまま
                    pass

                # 深さが +1 された場合
                elif level - cur_level == 1:
                    # ブロック作成
                    block = Block(Block.Kind.QUOTE, cur_block)
                    # カレントブロックに登録
                    cur_block.subitems.append(block)
                    # カレントブロックを移動
                    cur_block = block

                # 深さが +2 以上された場合
                else:
                    # その行は捨てる
                    continue

                # 深さを更新
                cur_level = level

                # ブロックに情報を連結
                inlines = self._parse_inline(match[2])
                cur_block.subitems.extend(inlines)
            else:
                # 最後までスキップ
                skip = len(lines)

            done = True

        return done, skip

    def _parse_block_table(self, cur_block, lines, i):
        '''
        ブロック：表を解析
        '''
        done = False
        skip = i

        match = self._regexb[Block.Kind.TABLE][0].match(lines[i])
        if match:
            # ブロック作成
            block = Block(Block.Kind.TABLE, cur_block)

            # 現在行からループを進める
            for j, sub_line in enumerate(lines[i:]):
                # マッチしなくなったらループ終了
                idx = 1 if j == 1 else 0
                match = self._regexb[Block.Kind.TABLE][idx].match(sub_line)
                if not match:
                    # ループを進めた位置の直前までスキップさせる
                    skip = i + j - 1
                    break

                # 区切り行の場合は次の行へ
                if j == 1:
                    continue

                # 列を分割
                cells = sub_line.split('|')
                # 先頭と末尾は余分な情報となるため削除
                # セル内の前後の空白も削除
                if len(cells) < 2:
                    continue
                cells = [c.strip() for c in cells[1:-1]]

                # 全セルをインライン要素として解析
                cell_inlines = []
                for cell in cells:
                    inlines = self._parse_inline(cell)
                    cell_inlines.append(inlines)

                # ブロックに情報を連結
                block.subitems.append(cell_inlines)
            else:
                # 最後までスキップ
                skip = len(lines)

            # 全行の列数をチェック
            col_counts = [len(r) for r in block.subitems]
            # 列数に不一致がなければ
            if len([{col_counts}]) == 1:
                # カレントブロックに登録
                cur_block.subitems.append(block)
                done = True

        return done, skip

    def _parse_block_list(self, cur_block, lines, i):
        '''
        ブロック：リストを解析
        '''
        done = False
        skip = i

        def match_some_list(md_line):
            '''
            3種類のリストのいずれかにマッチするか調べる
            '''
            match_n = self._regexb[Block.Kind.LIST].match(md_line)
            match_o = self._regexb[Block.Kind.LIST_ORDERED].match(md_line)
            match_c = self._regexb[Block.Kind.LIST_CHECK].match(md_line)

            kind = None
            d, _ = self._check_indent(md_line)
            level = d + 1
            text = ''
            if match_c:
                kind = Block.Kind.LIST_CHECK
                text = match_c[3]
            elif match_o:
                kind = Block.Kind.LIST_ORDERED
                text = match_o[2]
            elif match_n:
                kind = Block.Kind.LIST
                text = match_n[2]

            return kind, level, text

        def match_inner_list(cur_block, cur_level, lines, i):
            '''
            リストに内包可能なブロックであれば登録する
            '''
            # リスト内のインデントに制限を設けないため cur_level は未使用

            # 画像
            done, skip = self._parse_block_image(cur_block, lines, i)
            if done:
                return done, skip

            # コード
            done, skip = self._parse_block_code(cur_block, lines, i)
            if done:
                return done, skip

            # 引用
            done, skip = self._parse_block_quote(cur_block, lines, i)
            if done:
                return done, skip

            # 表
            done, skip = self._parse_block_table(cur_block, lines, i)
            if done:
                return done, skip

            # 段落
            done, skip = self._parse_block_para(cur_block, lines, i)
            if done:
                # リストの直後の段落はリスト文字列の続きと見なす
                # それ以外の段落ブロックは削除

                # 末尾に登録された段落ブロックを取り出す
                para = cur_block.subitem.pop(-1)

                # さらに前がリスト文字列（インライン要素）
                if len(cur_block.subitem) == 0 or \
                   isinstance(cur_block.subitem[-1], Inline):
                    # 段落の文字列を連結する
                    cur_block.subitem.extend(para.subitems)

                return done, skip

        # リストにマッチするかチェック
        kind, level, text = match_some_list(lines[i])

        if kind:
            cur_level = 0
            skip_j = -1

            # 現在行からループを進める
            for j, sub_line in enumerate(lines[i:]):
                if j <= skip_j: continue

                # リストにマッチするかチェック
                kind, level, text = match_some_list(sub_line)
                if kind:
                    # 深さが減少した場合
                    if level < cur_level:
                        # カレントブロックを上へ移動
                        for i in range(cur_level - level):
                            cur_block = cur_block.parent

                        # ブロック作成
                        block = Block(kind, cur_block.parent)
                        # カレントブロックと同階層に登録
                        cur_block.parent.subitems.append(block)
                        # カレントブロックを移動
                        cur_block = block

                    # 深さが同じ場合
                    elif level == cur_level:
                        # ブロック作成
                        block = Block(kind, cur_block.parent)
                        # カレントブロックと同階層に登録
                        cur_block.parent.subitems.append(block)
                        # カレントブロックを移動
                        cur_block = block

                    # 深さが +1 された場合
                    elif level - cur_level == 1:
                        # ブロック作成
                        block = Block(kind, cur_block)
                        # カレントブロックに登録
                        cur_block.subitems.append(block)
                        # カレントブロックを移動
                        cur_block = block

                    # 深さが +2 以上された場合
                    else:
                        # その行は捨てる
                        continue

                    # 深さを更新
                    cur_level = level

                    # ブロックに情報を連結
                    inlines = self._parse_inline(text)
                    cur_block.subitems.extend(inlines)

                else:
                    # リストに内包可能なブロックをチェック
                    done, skip_j = match_inner_list(cur_block, cur_level, lines[i:], j)
                    if not done:
                        # ループを進めた位置の直前までスキップさせる
                        skip = i + j - 1
                        break
            else:
                # 最後までスキップ
                skip = len(lines)

            done = True

        return done, skip

    def _parse_block_para(self, cur_block, lines, i):
        '''
        ブロック：段落を解析

        段落は必ず他のブロックでないかチェックした後の行を対象とするため１行ずつ解析する
        段落が複数行連続している場合は連結していく手法をとる
        '''
        done = False
        skip = i

        match = self._regexb[Block.Kind.PARA].match(lines[i])
        if match:
            # インライン要素に変換
            inlines = self._parse_inline(match[1])

            # 最終要素がプレーンテキストの場合は、末尾の改行チェック
            if inlines[-1].kind == Inline.Kind.PLANE:
                # 末尾に半角SPが2つある場合は改行コードに変換する
                if re.search(r' {2}$', inlines[-1].texts[0]):
                    inlines[-1].texts[0] = inlines[-1].texts[0][:-2] + '\n'

            # 直前のブロックが段落の場合
            block = None
            if cur_block.subitems and cur_block.subitems[-1].kind == Block.Kind.PARA:
                # 直前のブロックに連結
                cur_block.subitems[-1].subitems.extend(inlines)
            else:
                # ブロック作成
                block = Block(Block.Kind.PARA, cur_block)
                block.subitems.extend(inlines)
                # カレントブロックに登録
                cur_block.subitems.append(block)

            done = True

        return done, skip

    def _parse_inline(self, line):
        '''
        インライン要素を解析
        '''
        inlines = []
        words = []

        # インライン要素のワードに分割
        # 正規表現オブジェクトのsplitではうまくいかない
        pos = 0
        while True:
            match = self._regext_all.search(line, pos)
            if match:
                words.append(line[pos:match.start()])
                words.append(line[match.start():match.end()])
                pos = match.end()
            else:
                words.append(line[pos:])
                break

        # 空文字列を除外
        words = [w for w in words if w]

        # 要素をループ
        for word in words:
            inline = Inline()
            # インライン種別を順に該当チェック
            for kind, regext in self._regext.items():
                match = regext.match(word)
                if match:
                    # 該当するインライン要素として格納
                    inline.kind = kind

                    # 取得するテキストのグループ番号
                    for gid in self._regext_gid[kind]:
                        if match[gid] is not None:
                            inline.texts.append(match[gid])

                    break

            # 該当なしの場合はプレーンテキスト
            else:
                inline.kind = Inline.Kind.PLANE
                inline.texts.append(word)

            # インライン要素として登録
            inlines.append(inline)

        return inlines

    def _check_indent(self, text):
        '''
        文字列のインデントを調べる
        '''
        INDENT_WIDTH = 4

        depth = 0
        deindent = text

        # チェック
        match = re.match(r'^(\s*)(.*)$', text)
        if match:
            sp_cnt = match[1].count(' ')
            tab_cnt = match[1].count('\t')
            # スペースの数をチェック
            if sp_cnt % INDENT_WIDTH:
                depth = sp_cnt // INDENT_WIDTH + tab_cnt
                deindent = match[2]

        return depth, deindent

class ReviewRenderer:
    '''
    Re:VIEWレンダラ
    '''

    def __init__(self):
        '''
        コンストラクタ
        '''
        pass

    def __call__(self, doc):
        '''
        ()演算子：レンダリング処理
        '''
        lines = []

        # レンダリング
        self._render(doc)

        return lines

    def _render(self, block, depth=0):
        '''
        全ブロックを再帰的にレンダリング
        '''
        lines = []
        for subitem in block.subitems:
            # デバッグ用プリント
            if DEBUG_MODE:
                print('  ' * depth + str(subitem))

            if isinstance(subitem, Block):
                # 内部を再帰的にレンダリング
                self._render(subitem, depth + 1)
            elif isinstance(subitem, Inline):
                # テキスト化
                pass

        return lines


if __name__ == '__main__':
    # 引数解析
    parser = argparse.ArgumentParser(description='Convert Markdown file to Re:VIEW file.')
    parser.add_argument('input_path', help='Input File Path. (Markdown file)')
    parser.add_argument('output_path', help='Output File Path. (Re:VIEW file)')
    parser.add_argument('-s', '--starter', action='store_true', help='Use Re:VIEW Stareter Extentions.')
    args = parser.parse_args()

    # Markdownファイル読み込み
    with open(args.input_path, 'r') as f:
        md_lines = [l.rstrip('\r\n') for l in f.readlines()]    # 改行を除去

    # Markdown -> 文書全体ブロック
    md_parser = MarkdownParser()
    md_doc = md_parser(md_lines)

    # 文書ブロック -> Re:VIEW
    re_renderer = ReviewRenderer()
    re_lines = re_renderer(md_doc)

    # Re:VIEWファイル書き込み
    with open(args.output_path, 'w') as f:
        f.write('\n'.join(re_lines))
