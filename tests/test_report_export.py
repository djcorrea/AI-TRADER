from build_report import portable_files


def test_portable_export_excludes_private_runtime_and_dependencies(tmp_path):
    for name in ['run.py','lab/features.py','models/registry.json','results/report.json',
                 '.env','.git/config','.venv/lib/private.py','paper/paper.sqlite',
                 'data/parquet/BTCUSDT/1m/raw.parquet','research/checkpoint.json']:
        path=tmp_path/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text('fixture')
    (tmp_path/'lab/linked.py').symlink_to('/etc/passwd')
    names={str(p.relative_to(tmp_path)) for p in portable_files(tmp_path)}
    assert names=={'run.py','lab/features.py','models/registry.json','results/report.json'}
