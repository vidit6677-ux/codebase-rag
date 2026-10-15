from pathlib import Path

from backend.chunker import chunk_file


def test_chunk_file_extracts_class_and_function():
    source = Path(__file__).parent / "fixtures" / "example.cpp"
    chunks = chunk_file(str(source))

    class_chunk = next(chunk for chunk in chunks if chunk.kind == "class")
    function_chunk = next(chunk for chunk in chunks if chunk.kind == "function")

    assert "class Greeter" in class_chunk.text
    assert "int add" in function_chunk.text
    assert (function_chunk.start_line, function_chunk.end_line) == (7, 9)
