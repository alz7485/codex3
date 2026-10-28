"""Independent editor entry point; does not instantiate the resident Controller."""
if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description='Yohaku コンテンツエディタ')
    parser.add_argument('--content-root')
    args=parser.parse_args()
    from companion.content_editor import run
    raise SystemExit(run(args.content_root))
