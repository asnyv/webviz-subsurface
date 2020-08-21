def pytest_addoption(parser):
    parser.addoption(
        "--testdata",
        action="store",
        default="./",
        help="Path to where a clone of webviz-subsurface-testdata is stored",
    )
