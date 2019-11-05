"""
debug.py
  Print intermidiate data to stdout.
"""


import argparse
import mdparser
from mdparser import Block, Inline


def main():
    '''
    メイン
    '''
    # 引数解析
    parser = argparse.ArgumentParser(description='Print intermidiate data to stdout.')
    parser.add_argument('input_path', help='Input File Path. (Markdown file)')
    args = parser.parse_args()

    # Markdownファイル読み込み
    with open(args.input_path, 'r', encoding='utf-8') as f:
        md_lines = [l.rstrip('\r\n') for l in f.readlines()]    # 改行を除去

    # Markdown -> 文書全体ブロック
    md_parser = mdparser.MarkdownParser()
    md_doc = md_parser(md_lines)

    # デバッグ用プリント
    block_print(md_doc)


def block_print(block, depth=0):
    '''
    ブロックを再帰的に表示
    '''
    for subitem in block.subitems:
        # ブロック・インライン要素を表示
        print('  ' * depth + str(subitem))

        if isinstance(subitem, Block):
            # 内部を再帰的に表示
            block_print(subitem, depth + 1)


if __name__ == '__main__':
    main()
