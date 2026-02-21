from src import _version


def test_generated_version_module_exports_values():
    assert isinstance(_version.__version__, str)
    assert _version.__version__ == _version.version
    assert isinstance(_version.__version_tuple__, tuple)
    assert _version.__version_tuple__ == _version.version_tuple
    assert isinstance(_version.__commit_id__, str)
    assert _version.__commit_id__ == _version.commit_id
