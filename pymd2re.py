"""
pymd2re.py
  Convert Markdown file to Re:VIEW file.
"""


import argparse
from enum import IntEnum, auto
import re


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
        ITALIC = auto()         # イタリック
        BOLD = auto()           # ボールド
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
        QUOTE_TOP = auto()      # 引用(データ先頭)
        QUOTE_DATA = auto()     # 引用
        TABLE_TOP = auto()      # 表(データ先頭)
        TABLE_ROW = auto()      # 表の行
        TABLE_ROW_H = auto()    # 表のヘッダ行
        TABLE_CELL = auto()     # 表のセル
        LIST_TOP = auto()       # リスト(データ先頭)
        LIST_NORMAL = auto()    # 番号無しリスト
        LIST_ORDERED = auto()   # 番号付きリスト
        LIST_CHECK = auto()     # チェックリスト
        PARA = auto()           # 段落

    def __init__(self, kind=Kind.DOCUMENT, parent=None, linenum=0):
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
        self.level = 0     # ヘッダ、引用、リストで使用する
        # 解析元の行番号
        self.linenum = linenum

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

    # 定数
    INDENT_WIDTH = 4    # インデント文字幅

    def __init__(self):
        '''
        コンストラクタ
        '''
        # ブロックのための正規表現オブジェクト
        # リストに内包可能なものは先頭のインデントを許容（\s*）
        self._regexb = {}
        self._regexb[Block.Kind.COMMENT] = []                                                   # コメント
        self._regexb[Block.Kind.COMMENT].append(re.compile(r'^\s*<!-{2,}(.*?)(-{2,}>)?$'))      #   [0] 開始 ※同じ行で終了する場合を考慮
        self._regexb[Block.Kind.COMMENT].append(re.compile(r'^\s*(.*?)-{2,}>'))                 #   [1] 終了
        self._regexb[Block.Kind.HEADER] = []                                                    # 見出し
        self._regexb[Block.Kind.HEADER].append(re.compile(r'^(#+) (.*)'))                       #   [0] 行頭が #
        self._regexb[Block.Kind.HEADER].append(re.compile(r'^(={3,}|-{3,})$'))                  #   [1] 次行が === ---
        self._regexb[Block.Kind.HR] = re.compile(r'^(\*{3,}|-{3,}|_{3,})$')                     # 水平線
        self._regexb[Block.Kind.IMAGE] = re.compile(r'^\s*!\[(.+?)\]\((.+?)( +"(.+?)")?\)$')    # 画像
        self._regexb[Block.Kind.PRE] = re.compile(r'^ {4}(.*)$')                                # 整形済みテキスト
        self._regexb[Block.Kind.CODE] = re.compile(r'^\s*`{3}(.*)$')                            # コード
        self._regexb[Block.Kind.QUOTE_DATA] = re.compile(r'^\s*(>+)(.*)$')                      # 引用
        self._regexb[Block.Kind.TABLE_ROW] = []                                                 # 表
        self._regexb[Block.Kind.TABLE_ROW].append(re.compile(r'^\s*(\|\s*[^\|]*?\s*)+\|$'))     #   [0] データ行
        self._regexb[Block.Kind.TABLE_ROW].append(re.compile(r'^\s*(\|\s*(:)?-+?(:)?\s*)+\|$')) #   [1] 区切り行
        self._regexb[Block.Kind.LIST_NORMAL] = re.compile(r'^(-|\*) (.*)$')                     # 番号無しリスト
        self._regexb[Block.Kind.LIST_ORDERED] = re.compile(r'^(\d+\.) (.*)$')                   # 番号付きリスト
        self._regexb[Block.Kind.LIST_CHECK] = re.compile(r'^(-|\*) \[( |x|X)?\] (.*)$')         # チェックリスト
        self._regexb[Block.Kind.PARA] = re.compile(r'^\s*(.+)$')                                # 段落

        # インラインのための正規表現
        restr = {}
        restr[Inline.Kind.COMMENT] = r'<!-{2,}([^-]*?)-{2,}>'                       # <!--xxx-->
        restr[Inline.Kind.ITALIC] = r'\*{1}([^\*]+?)\*{1}|_{1}([^_]+?)_{1}'         # *xxx* or _xxx_
        restr[Inline.Kind.BOLD] = r'\*{2}([^\*]+?)\*{2}|_{2}([^_]+?)_{2}'           # **xxx** or __xxx__
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
        self._regext_gid[Inline.Kind.ITALIC] = (1, 2)       # イタリック
        self._regext_gid[Inline.Kind.BOLD] = (1, 2)         # ボールド
        self._regext_gid[Inline.Kind.BOLD_ITALIC] = (1, 2)  # ボールド＆イタリック
        self._regext_gid[Inline.Kind.CODE] = (1,)           # コード
        self._regext_gid[Inline.Kind.STRIKE] = (1,)         # 取消線
        self._regext_gid[Inline.Kind.EMOJI] = (1,)          # 絵文字
        self._regext_gid[Inline.Kind.LINK] = (1, 2, 3)      # リンク
        self._regext_gid[Inline.Kind.IMAGE] = (1, 2, 4)     # 画像

        # インラインのための正規表現オブジェクト
        self._regext = {}
        self._regext[Inline.Kind.COMMENT] = re.compile(restr[Inline.Kind.COMMENT])          # コメント
        self._regext[Inline.Kind.ITALIC] = re.compile(restr[Inline.Kind.ITALIC])            # イタリック
        self._regext[Inline.Kind.BOLD] = re.compile(restr[Inline.Kind.BOLD])                # ボールド
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
            if i <= skip:
                continue

            # 空行はスキップ
            if len(cur_line) == 0:
                continue

            # ブロック解析のための関数リスト
            # ※解析を行う順番に定義
            # ※入力/出力が一致している必要あり（ダックタイピング）
            parse_block_funcs = [
                self._parse_block_comment,          # コメント
                self._parse_block_header_single,    # 見出し(行頭が # のケース)
                self._parse_block_hr,               # 水平線
                self._parse_block_image,            # 画像
                self._parse_block_pre,              # 整形済みテキスト
                self._parse_block_code,             # コード
                self._parse_block_quote,            # 引用
                self._parse_block_table,            # 表
                self._parse_block_list,             # リスト
                self._parse_block_header_multiple,  # 見出し(次行が === --- のケース)
                self._parse_block_para,             # 段落
            ]

            # ブロック解析関数を処理されるまで順に呼び出す
            for func in parse_block_funcs:
                done, skip = func(doc, lines, i)
                if done:
                    break

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
            block = Block(Block.Kind.COMMENT, cur_block, i + 1)
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
            block = Block(Block.Kind.HEADER, cur_block, i + 1)
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
                block = Block(Block.Kind.HEADER, cur_block, i + 1)
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
            block = Block(Block.Kind.HR, cur_block, i + 1)
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
            block = Block(Block.Kind.IMAGE, cur_block, i + 1)
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
                sub_lines.append(sub_line)
            else:
                # 最後までスキップ
                skip = len(lines)

            # ブロック作成
            block = Block(Block.Kind.PRE, cur_block, i + 1)
            # 情報を格納
            inline = Inline()
            inline.texts.append('\n'.join(sub_lines))
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

            # インデントの深さをチェック
            indent_depth, _ = self._check_indent(lines[i])

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
                    sub_line = self._delete_indent(sub_line, indent_depth)
                    sub_lines.append(sub_line)
                else:
                    # 最後までスキップ
                    skip = len(lines)

            # ブロック作成
            block = Block(Block.Kind.CODE, cur_block, i + 1)
            # 情報を格納
            inline = Inline()
            inline.texts.append('\n'.join(sub_lines))
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

        match = self._regexb[Block.Kind.QUOTE_DATA].match(lines[i])
        if match:
            # 引用ヘッドを作成して登録
            cur_block_backup = cur_block
            block = Block(Block.Kind.QUOTE_TOP, cur_block, i + 1)
            cur_block.subitems.append(block)
            cur_block = block

            cur_level = 0

            # 現在行からループを進める
            for j, sub_line in enumerate(lines[i:]):
                # マッチしなくなったらループ終了
                match = self._regexb[Block.Kind.QUOTE_DATA].match(sub_line)
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
                    block = Block(Block.Kind.QUOTE_DATA, cur_block, i + j + 1)
                    block.level = level
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
                inlines = self._parse_inline(match[2], has_lf=True)

                cur_block.subitems.extend(inlines)
            else:
                # 最後までスキップ
                skip = len(lines)

            # カレントブロックを引用解析前に戻す
            cur_block = cur_block_backup

            done = True

        return done, skip

    def _parse_block_table(self, cur_block, lines, i):
        '''
        ブロック：表を解析
        '''
        done = False
        skip = i

        match = self._regexb[Block.Kind.TABLE_ROW][0].match(lines[i])
        if match:
            # ブロック作成
            block_table_top = Block(Block.Kind.TABLE_TOP, cur_block, i + 1)

            # 現在行からループを進める
            for j, sub_line in enumerate(lines[i:]):
                # マッチしなくなったらループ終了
                idx = 1 if j == 1 else 0
                match = self._regexb[Block.Kind.TABLE_ROW][idx].match(sub_line)
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

                # 表の行ブロックを作成
                kind = Block.Kind.TABLE_ROW_H if j == 0 else Block.Kind.TABLE_ROW
                block_row = Block(kind, block_table_top, i + j + 1)
                # 行内のセルをインライン要素として解析しながら登録
                for cell in cells:
                    # 表のセルブロックを作成
                    block_cell = Block(Block.Kind.TABLE_CELL, block_row, i + j + 1)
                    inlines = self._parse_inline(cell)
                    block_cell.subitems.extend(inlines)
                    # 行ブロックに連結
                    block_row.subitems.append(block_cell)

                # 表ブロックに行ブロックを連結
                block_table_top.subitems.append(block_row)

            else:
                # 最後までスキップ
                skip = len(lines)

            # 全行の列数をチェック
            col_counts = [len(row.subitems) for row in block_table_top.subitems]
            # 列数に不一致がなければ
            if len(list(set(col_counts))) == 1:
                # カレントブロックに登録
                cur_block.subitems.append(block_table_top)
                done = True

        return done, skip

    def _parse_block_list(self, cur_block, lines, i):
        '''
        ブロック：リストを解析
        '''
        done = False
        skip = i

        def match_some_list(line):
            '''
            3種類のリストのいずれかにマッチするか調べる
            '''
            kind = None
            depth, text = self._check_indent(line)
            level = depth + 1

            # 3種類のリストのマッチをチェック
            match_n = self._regexb[Block.Kind.LIST_NORMAL].match(text)
            match_o = self._regexb[Block.Kind.LIST_ORDERED].match(text)
            match_c = self._regexb[Block.Kind.LIST_CHECK].match(text)

            if match_c:
                kind = Block.Kind.LIST_CHECK
                text = match_c[3]
            elif match_o:
                kind = Block.Kind.LIST_ORDERED
                text = match_o[2]
            elif match_n:
                kind = Block.Kind.LIST_NORMAL
                text = match_n[2]

            return kind, level, text

        def match_inner_list(cur_block, cur_level, lines, i):
            '''
            リストに内包可能なブロックであれば登録する
            '''
            # リスト内のインデントに制限を設けないため cur_level は未使用

            # ブロック解析のための関数リスト
            # ※解析を行う順番に定義
            # ※入力/出力が一致している必要あり（ダックタイピング）
            parse_block_funcs = [
                self._parse_block_comment,          # コメント
                self._parse_block_image,            # 画像
                self._parse_block_code,             # コード
                self._parse_block_quote,            # 引用
                self._parse_block_table,            # 表
                self._parse_block_para,             # 段落
            ]

            # ブロック解析関数を処理されるまで順に呼び出す
            for func in parse_block_funcs:
                done, skip = func(cur_block, lines, i)
                if done:
                    break

            # リストの直後の段落はリスト文字列の続きと見なす
            # それ以外の段落ブロックは削除

            # 上で解析関数が処理済みとなっている場合
            if done:
                # 末尾に登録されたブロックを取り出す
                block = cur_block.subitems.pop(-1)

                # 段落ブロックの場合
                if block.kind == Block.Kind.PARA:
                    # さらに前がリスト文字列（インライン要素）の場合
                    if len(cur_block.subitems) == 0 or \
                       isinstance(cur_block.subitems[-1], Inline):
                        # 段落の文字列を連結する
                        cur_block.subitems.extend(block.subitems)
                else:
                    # 段落ブロックでなければ戻す
                    cur_block.subitems.append(block)

            return done, skip

        # リストにマッチするかチェック
        kind, level, text = match_some_list(lines[i])

        if kind:
            # リストヘッドを作成して登録
            cur_block_backup = cur_block
            block = Block(Block.Kind.LIST_TOP, cur_block, i + 1)
            cur_block.subitems.append(block)
            cur_block = block

            cur_level = 0
            skip_j = -1

            # 現在行からループを進める
            for j, sub_line in enumerate(lines[i:]):
                if j <= skip_j:
                    continue

                # リストにマッチするかチェック
                kind, level, text = match_some_list(sub_line)
                if kind:
                    # 深さが減少した場合
                    if level < cur_level:
                        # カレントブロックを上へ移動
                        for _ in range(cur_level - level):
                            cur_block = cur_block.parent

                        # ブロック作成
                        block = Block(kind, cur_block.parent, i + j + 1)
                        block.level = level
                        # カレントブロックと同階層に登録
                        cur_block.parent.subitems.append(block)
                        # カレントブロックを移動
                        cur_block = block

                    # 深さが同じ場合
                    elif level == cur_level:
                        # ブロック作成
                        block = Block(kind, cur_block.parent, i + j + 1)
                        block.level = level
                        # カレントブロックと同階層に登録
                        cur_block.parent.subitems.append(block)
                        # カレントブロックを移動
                        cur_block = block

                    # 深さが +1 された場合
                    elif level - cur_level == 1:
                        # ブロック作成
                        block = Block(kind, cur_block, i + j + 1)
                        block.level = level
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
                    done, skip_j = match_inner_list(cur_block, cur_level, lines, i + j)
                    if not done:
                        # ループを進めた位置の直前までスキップさせる
                        skip = i + j - 1
                        break
            else:
                # 最後までスキップ
                skip = len(lines)

            # カレントブロックをリスト解析前に戻す
            cur_block = cur_block_backup

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
            inlines = self._parse_inline(match[1], has_lf=True)

            block = None
            # 直前のブロックが段落 かつ 直前の行が空行ではない場合
            if cur_block.subitems and cur_block.subitems[-1].kind == Block.Kind.PARA and \
               i > 0 and lines[i-1] != '':
                # 段落の継続と見なし、直前のブロックに連結
                cur_block.subitems[-1].subitems.extend(inlines)
            else:
                # 新しい段落のためのブロック作成
                block = Block(Block.Kind.PARA, cur_block, i + 1)
                block.subitems.extend(inlines)
                # カレントブロックに登録
                cur_block.subitems.append(block)

            done = True

        return done, skip

    def _parse_inline(self, line, has_lf=False):
        '''
        インライン要素を解析
        '''
        inlines = []
        words = []

        # この時点で先頭にスペースがある場合は除去する
        line = line.lstrip()

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

        # 末尾の改行コードを解析する場合
        if has_lf and inlines:
            # 最終要素がプレーンテキストの場合は、末尾の改行チェック
            if inlines[-1].kind == Inline.Kind.PLANE:
                # 末尾に半角SPが2つある場合は改行コードに変換する
                if re.search(r' {2}$', inlines[-1].texts[0]):
                    inlines[-1].texts[0] = inlines[-1].texts[0][:-2] + '\n'

        return inlines

    def _check_indent(self, text):
        '''
        文字列のインデントを調べる
        '''

        depth = 0
        deindent = text

        # チェック
        match = re.match(r'^(\s*)(.*?)$', text)
        if match:
            sp_cnt = match[1].count(' ')
            tab_cnt = match[1].count('\t')
            # スペースの数をチェック
            if sp_cnt % MarkdownParser.INDENT_WIDTH == 0:
                depth = sp_cnt // MarkdownParser.INDENT_WIDTH + tab_cnt
                deindent = match[2]

        return depth, deindent

    def _delete_indent(self, text, depth):
        '''
        文字列のインデントを指定した深さ分だけ削除する
        指定した深さよりインデントが浅い場合は全インデントを削除する
        '''

        # 半角SPまたはタブ文字のインデントを表す正規表現オブジェクト
        regex_indent = re.compile(
            r'^(' +
            (r' ' * MarkdownParser.INDENT_WIDTH) +
            r'|\t)'
        )

        # 指定した深さの回数処理する
        for _ in range(depth):
            # 1レベル分のインデントを削除
            text = regex_indent.sub('', text)

        return text

class ReviewRenderer:
    '''
    Re:VIEWレンダラ
    '''

    # 列挙型
    class MessageLevel(IntEnum):
        '''
        メッセージレベル
        '''
        DEBUG = auto()
        INFO = auto()
        WARNING = auto()
        ERROR = auto()


    def __init__(self):
        '''
        コンストラクタ
        '''
        pass

    def __call__(self, doc):
        '''
        ()演算子：レンダリング処理
        '''

        # レンダリング
        output = self._render_block(doc)

        return output

    def _render_block(self, block):
        '''
        ブロックを再帰的にレンダリング
        '''
        # 出力文字列は明示的に改行コード(\n)を格納すること
        output = ''

        # このブロックのヘッダ文字列
        block_head = ''
        # このブロック内の行のヘッダ文字列
        line_head = ''
        # このブロック内の行のフッタ文字列
        line_foot = ''
        # このブロックの降った文字列
        block_foot = ''
        # このブロックの出力可否
        is_output = True

        # 文書全体
        if block.kind == Block.Kind.DOCUMENT:
            pass

        # コメント
        elif block.kind == Block.Kind.COMMENT:
            line_head = '#@# '
            block_foot = '\n'

        # 見出し
        elif block.kind == Block.Kind.HEADER:
            level = block.level
            if level >= 6:
                level = 5
                # 警告
                self._print_error('６段階以上の見出しは使用できません。５段階目として出力します。', ReviewRenderer.MessageLevel.WARNING, block.linenum)

            block_head = '=' * level + ' '
            block_foot = '\n\n'

        # 水平線
        elif block.kind == Block.Kind.HR:
            is_output = False
            # 警告
            self._print_error('水平線は使用できません。出力対象外とします。', ReviewRenderer.MessageLevel.WARNING, block.linenum)
            block_foot = '\n\n'

        # 画像
        elif block.kind == Block.Kind.IMAGE:
            block_foot = '\n\n'

        # 整形済みテキスト
        elif block.kind == Block.Kind.PRE:
            block_head = '//emlist{\n'
            block_foot = '\n//}\n\n'

        # コード
        elif block.kind == Block.Kind.CODE:
            block_head = '//emlist{\n'
            block_foot = '\n//}\n\n'

        # 引用(データ先頭)
        elif block.kind == Block.Kind.QUOTE_TOP:
            block_foot = '\n'

        # 引用
        elif block.kind == Block.Kind.QUOTE_DATA:
            if block.level >= 2:
                # 警告
                self._print_error('２段階以上の引用は使用できません。１段階目の内容の一部として出力します。', ReviewRenderer.MessageLevel.WARNING, block.linenum)
            else:
                block_head = '//quote{\n'
                block_foot = '//}\n\n'
            line_foot = '\n'

        # 表(データ先頭)
        elif block.kind == Block.Kind.TABLE_TOP:
            block_head = '//table[][]{\n'
            block_foot = '//}\n\n'

        # 表の行
        elif block.kind == Block.Kind.TABLE_ROW:
            block_foot = '\n'

        # 表のヘッダ行
        elif block.kind == Block.Kind.TABLE_ROW_H:
            block_foot = '\n------\n'

        # 表のセル
        elif block.kind == Block.Kind.TABLE_CELL:
            line_foot = '\t'

        # リスト(データ先頭)
        elif block.kind == Block.Kind.LIST_TOP:
            block_foot = '\n'

        # 番号無しリスト
        elif block.kind == Block.Kind.LIST_NORMAL:
            block_head = '*' * block.level + ' '
            line_foot = '\n'

        # 番号付きリスト
        elif block.kind == Block.Kind.LIST_ORDERED:
            if block.level >= 2:
                is_output = False
                # 警告
                self._print_error('番号付きリストのネストは使用できません。出力対象外とします。', ReviewRenderer.MessageLevel.WARNING, block.linenum)
            else:
                block_head = '1. '
            line_foot = '\n'

        # チェックリスト
        elif block.kind == Block.Kind.LIST_CHECK:
            block_head = '*' * block.level + ' '
            # 警告
            self._print_error('チェックリストは使用できません。番号無しリストとして出力します。', ReviewRenderer.MessageLevel.WARNING, block.linenum)
            line_foot = '\n'

        # 段落
        elif block.kind == Block.Kind.PARA:
            block_foot = '\n\n'

        def convert_text(text, head, foot):
            '''
            テキストを出力文字列に変換
            '''
            # テキストを行に分割
            lines = text.split('\n')
            # 全行にヘッダとフッタを連結
            lines = [(head + l + foot) for l in lines]
            # １つのテキストに戻す
            text = '\n'.join(lines)

            return text

        # ブロックヘッダを出力
        output += block_head

        text = None

        # 内部要素をループ
        for subitem in block.subitems:
            # ブロック
            if isinstance(subitem, Block):
                # ここまでのテキストを出力
                if text is not None:
                    output += convert_text(text, line_head, line_foot)
                    text = None

                # 内部ブロックを再帰的にレンダリング
                output += self._render_block(subitem)

            # インライン
            elif isinstance(subitem, Inline):
                # インライン要素をレンダリングしてテキストを保持
                text_buf = self._render_inline(subitem, block.linenum)
                if text is not None:
                    text += text_buf
                else:
                    text = text_buf

        # ここまでのテキストを出力
        if text is not None:
            output += convert_text(text, line_head, line_foot)
            text = None

        # 特定のブロック処理
        if block.kind == Block.Kind.TABLE_ROW or \
           block.kind == Block.Kind.TABLE_ROW_H:
            # TABLE_CELL の処理で入れた末尾のタブ文字を削除
            output = output.rstrip('\t')
        elif block.kind == Block.Kind.TABLE_CELL:
            # 空文字列は . とする
            if not output:
                output = '.'

        # ブロックフッタを出力
        output += block_foot

        # 出力文字列を確定
        if not is_output:
            output = ''

        return output

    def _render_inline(self, inline, linenum):
        '''
        インライン要素をレンダリング
        '''
        output = ''

        # プレーンテキスト
        if inline.kind == Inline.Kind.PLANE:
            output = inline.texts[0]

        # コメント
        elif inline.kind == Inline.Kind.COMMENT:
            # 警告
            self._print_error('インラインコメントは使用できません。出力対象外とします。', ReviewRenderer.MessageLevel.WARNING, linenum)

        # イタリック
        elif inline.kind == Inline.Kind.ITALIC:
            output = '@<i>{' + inline.texts[0] + '}'

        # ボールド
        elif inline.kind == Inline.Kind.BOLD:
            output = '@<b>{' + inline.texts[0] + '}'

        # ボールド＆イタリック
        elif inline.kind == Inline.Kind.BOLD_ITALIC:
            output = '@<b>{' + inline.texts[0] + '}'
            # 警告
            self._print_error('ボールド＆イタリックは使用できません。ボールドで出力します。', ReviewRenderer.MessageLevel.WARNING, linenum)

        # コード
        elif inline.kind == Inline.Kind.CODE:
            output = '@<code>{' + inline.texts[0] + '}'

        # 取消線
        elif inline.kind == Inline.Kind.STRIKE:
            output = inline.texts[0]
            # 警告
            self._print_error('取消線は使用できません。プレーンテキストで出力します。', ReviewRenderer.MessageLevel.WARNING, linenum)

        # 絵文字
        elif inline.kind == Inline.Kind.EMOJI:
            # 警告
            self._print_error('絵文字は使用できません。出力対象外とします。', ReviewRenderer.MessageLevel.WARNING, linenum)

        # リンク
        elif inline.kind == Inline.Kind.LINK:
            if len(inline.texts) >= 2:
                output = '@<href>{%s,%s}' % (inline.texts[1], inline.texts[0])
            else:
                output = '@<href>{%s}' % (inline.texts[0])

        # 画像
        elif inline.kind == Inline.Kind.IMAGE:
            if len(inline.texts) >= 2:
                output += '//image[%s][%s]{\n' % (inline.texts[0], inline.texts[1])
            else:
                output += '//image[%s]{\n' % (inline.texts[0])
            output += '//}'

        return output

    def _print_error(self, msg, level, linenum):
        '''
        エラーメッセージを表示
        '''
        # メッセージレベル
        ltext = ''
        if level == ReviewRenderer.MessageLevel.DEBUG:
            ltext = 'Debug'
        elif level == ReviewRenderer.MessageLevel.INFO:
            ltext = 'Info '
        elif level == ReviewRenderer.MessageLevel.WARNING:
            ltext = 'Warn '
        elif level == ReviewRenderer.MessageLevel.ERROR:
            ltext = 'Error'

        # 表示
        print('{:5}: [Line={:>4}] {}'.format(ltext, linenum, msg))


def main():
    '''
    メイン
    '''
    # 引数解析
    parser = argparse.ArgumentParser(description='Convert Markdown file to Re:VIEW file.')
    parser.add_argument('input_path', help='Input File Path. (Markdown file)')
    parser.add_argument('output_path', help='Output File Path. (Re:VIEW file)')
    parser.add_argument('-s', '--starter', action='store_true', help='Use Re:VIEW Stareter Extentions.')
    parser.add_argument('-d', '--debug', action='store_true', help='Enable debug print. (stdout)')
    args = parser.parse_args()

    # Markdownファイル読み込み
    with open(args.input_path, 'r', encoding='utf-8') as f:
        md_lines = [l.rstrip('\r\n') for l in f.readlines()]    # 改行を除去

    # Markdown -> 文書全体ブロック
    md_parser = MarkdownParser()
    md_doc = md_parser(md_lines)

    # デバッグ用プリント
    if args.debug:
        block_print(md_doc)

    # 文書ブロック -> Re:VIEW
    re_renderer = ReviewRenderer()
    re_lines = re_renderer(md_doc)

    # Re:VIEWファイル書き込み
    with open(args.output_path, 'w', encoding='utf-8') as f:
        f.write(re_lines)


def block_print(block, depth=0):
    '''
    ブロックを再帰的に表示
    '''
    for subitem in block.subitems:
        # ブロック・インライン要素を表示
        print('  ' * depth + str(subitem))

        if isinstance(subitem, Block):
            # 内部を再帰的にレンダリング
            block_print(subitem, depth + 1)


if __name__ == '__main__':
    main()
