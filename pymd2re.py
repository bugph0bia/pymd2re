"""
pymd2re.py
  Convert Markdown file to Re:VIEW file.
"""


import argparse
from enum import IntEnum, auto
import mdparser
from mdparser import Block, Inline


class MessageLevel(IntEnum):
    '''
    列挙型：メッセージレベル
    '''
    DEBUG = auto()
    INFO = auto()
    WARNING = auto()
    ERROR = auto()


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
                self._print_error('６段階以上の見出しは使用できません。５段階目として出力します。', MessageLevel.WARNING, block.linenum)

            block_head = '=' * level + ' '
            block_foot = '\n\n'

        # 水平線
        elif block.kind == Block.Kind.HR:
            is_output = False
            # 警告
            self._print_error('水平線は使用できません。出力対象外とします。', MessageLevel.WARNING, block.linenum)
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
                self._print_error('２段階以上の引用は使用できません。１段階目の内容の一部として出力します。', MessageLevel.WARNING, block.linenum)
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
                self._print_error('番号付きリストのネストは使用できません。出力対象外とします。', MessageLevel.WARNING, block.linenum)
            else:
                block_head = '1. '
            line_foot = '\n'

        # チェックリスト
        elif block.kind == Block.Kind.LIST_CHECK:
            block_head = '*' * block.level + ' '
            # 警告
            self._print_error('チェックリストは使用できません。番号無しリストとして出力します。', MessageLevel.WARNING, block.linenum)
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
            self._print_error('インラインコメントは使用できません。出力対象外とします。', MessageLevel.WARNING, linenum)

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
            self._print_error('ボールド＆イタリックは使用できません。ボールドで出力します。', MessageLevel.WARNING, linenum)

        # コード
        elif inline.kind == Inline.Kind.CODE:
            output = '@<code>{' + inline.texts[0] + '}'

        # 取消線
        elif inline.kind == Inline.Kind.STRIKE:
            output = inline.texts[0]
            # 警告
            self._print_error('取消線は使用できません。プレーンテキストで出力します。', MessageLevel.WARNING, linenum)

        # 絵文字
        elif inline.kind == Inline.Kind.EMOJI:
            # 警告
            self._print_error('絵文字は使用できません。出力対象外とします。', MessageLevel.WARNING, linenum)

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
        if level == MessageLevel.DEBUG:
            ltext = 'Debug'
        elif level == MessageLevel.INFO:
            ltext = 'Info '
        elif level == MessageLevel.WARNING:
            ltext = 'Warn '
        elif level == MessageLevel.ERROR:
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
    #parser.add_argument('-s', '--starter', action='store_true', help='Use Re:VIEW Stareter Extentions.')   # 未対応
    args = parser.parse_args()

    # Markdownファイル読み込み
    with open(args.input_path, 'r', encoding='utf-8') as f:
        md_lines = [l.rstrip('\r\n') for l in f.readlines()]    # 改行を除去

    # Markdown -> 文書全体ブロック
    md_parser = mdparser.MarkdownParser()
    md_doc = md_parser(md_lines)

    # 文書ブロック -> Re:VIEW
    re_renderer = ReviewRenderer()
    re_lines = re_renderer(md_doc)

    # Re:VIEWファイル書き込み
    with open(args.output_path, 'w', encoding='utf-8') as f:
        f.write(re_lines)


if __name__ == '__main__':
    main()
