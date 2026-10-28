if __name__ == "__main__":
    import sys
    if len(sys.argv)>1 and sys.argv[1]=='--content-editor':
        import argparse
        parser=argparse.ArgumentParser(description='Yohaku content editor')
        parser.add_argument('--content-editor',action='store_true')
        parser.add_argument('--content-root')
        args=parser.parse_args()
        from companion.content_editor import run
        raise SystemExit(run(args.content_root))
    if len(sys.argv) > 1 and sys.argv[1] == '--self-check':
        import argparse
        parser = argparse.ArgumentParser(description='Check bundle assets and rendering without opening user data.')
        parser.add_argument('--self-check', required=True, metavar='REPORT_JSON')
        args = parser.parse_args()
        from companion.self_check import run
        raise SystemExit(run(args.self_check))
    from companion.ui import run
    run()
