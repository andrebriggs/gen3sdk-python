import json
import pytest, os, requests
from unittest.mock import call, MagicMock, patch


def test_get(sub):
    """
    tests:
    get_programs
    get_graphql_schema
    get_dictionary_all

    """
    with patch("gen3.submission.requests") as mock_request:
        mock_request.status_code = 200
        mock_request.get().text = '{ "key": "value" }'
        assert sub.get_programs()
        try:
            sub.get_graphql_schema()
        except:
            assert False
        try:
            sub.get_dictionary_all()
        except:
            assert False


def test_export_node(sub):
    """
    tests:
    export_node

    """
    with patch("gen3.submission.requests") as mock_request:
        mock_request.status_code = 200
        mock_request.get().text = '{ "key": "value" }'
        resp = sub.export_node("DEV", "test", "experiment", "json", "node_file.json")
        assert os.path.exists("node_file.json")
        os.remove("node_file.json")
        assert not os.path.exists("node_file.json")


def test_create_program(sub):

    with patch("gen3.submission.requests") as mock_request:
        mock_request.status_code = 200
        mock_request.json.return_value = '{ "key": "value" }'
        p = sub.create_program(
            {
                "dbgap_accession_number": "programmjm",
                "name": "programmjm",
                "type": "program",
            }
        )
        assert p


def test_delete_program(sub):

    with patch("gen3.submission.requests") as mock_request:
        mock_request.status_code = 200
        mock_request.json.return_value = '{ "key": "value" }'
        sub.delete_program("programmjm")


def test_create_project(sub):

    with patch("gen3.submission.requests") as mock_request:
        mock_request.status_code = 200
        mock_request.json.return_value = '{ "key": "value" }'
        pj = sub.create_project(
            "programmjm",
            {
                "code": "projectmjm",
                "dbgap_accession_number": "projectmjm",
                "name": "projectmjm",
                "availability_type": "Open",
            },
        )
        assert pj
        assert sub.get_projects("programmjm")
        assert sub.get_project_dictionary("programmjm", "projectmjm")


def test_delete_project(sub):

    with patch("gen3.submission.requests") as mock_request:
        mock_request.status_code = 200
        mock_request.json.return_value = '{ "key": "value" }'
        dpj = sub.delete_project("programmjm", "projectmjm")


def test_open_project(sub):
    with patch("gen3.submission.requests") as mock_request:
        mock_request.status_code = 200
        mock_request.json.return_value = '{ "key": "value" }'
        assert sub.open_project("programmjm", "projectmjm")


def test_submit_record(sub):
    with patch("gen3.submission.requests") as mock_request:
        mock_request.status_code = 200
        mock_request.json.return_value = '{ "key": "value" }'
        rec = sub.submit_record(
            "prog1",
            "proj1",
            {
                "projects": [{"code": "proj1"}],
                "submitter_id": "mjmartinson",
                "type": "experiment",
            },
        )
        assert rec


def test_export_record(sub):
    with patch("gen3.submission.requests") as mock_request:
        mock_request.status_code = 200
        mock_request.get().text = '{ "key": "value" }'
        sub.export_record("prog1", "proj1", "id", "json", "record_file.json")
        assert os.path.exists("record_file.json")
        os.remove("record_file.json")
        assert not os.path.exists("record_file.json")


def test_delete_record(sub):
    with patch("gen3.submission.requests") as mock_request:
        mock_request.status_code = 200
        mock_request.json.return_value = '{ "key": "value" }'
        sub.delete_record("prog1", "proj1", "id")


@patch("gen3.jobs.requests.post")
@patch("gen3.jobs.requests.delete")
def test_delete_nodes(requests_delete_mock, requests_post_mock, sub):
    def get_mocked_query_response(node_name, uuids):
        content = {"data": {node_name: [{"id": uuid} for uuid in uuids]}}
        return MagicMock(requests.Response, status_code=200, text=json.dumps(content))

    requests_post_mock.side_effect = [
        get_mocked_query_response("node1", ["id1", "id2"]),
        get_mocked_query_response("node1", []),
        get_mocked_query_response("node2", ["id3", "id4", "id5"]),
        get_mocked_query_response("node2", []),
    ]
    requests_delete_mock.side_effect = MagicMock(requests.Response)

    sub.delete_nodes(
        "program", "project", ["node1", "node2"], batch_size=2, verbose=False
    )

    requests_delete_mock.assert_has_calls(
        [
            call(
                "http://localhost/api/v0/submission/program/project/entities/id1,id2",
                auth=None,
            ),
            call(
                "http://localhost/api/v0/submission/program/project/entities/id3,id4",
                auth=None,
            ),
            call(
                "http://localhost/api/v0/submission/program/project/entities/id5",
                auth=None,
            ),
        ]
    )


def test_query(sub):
    with patch("gen3.submission.requests") as mock_request:
        mock_request.status_code = 200
        mock_request.post().text = '{ "key": "value" }'
        res = sub.query("{ experiment { submitter_id } }")
        assert res == {"key": "value"}
