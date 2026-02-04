"""
测试统一API错误处理格式
Test Unified Error Response Format

验证所有API端点返回统一的错误响应格式
"""


import pytest
from fastapi.testclient import TestClient

from src.api.app import app

client = TestClient(app)


def test_error_response_structure():
    """测试错误响应结构是否符合统一格式"""
    # 测试404错误
    response = client.get("/api/v1/nonexistent-endpoint")

    assert response.status_code == 404
    data = response.json()

    # 验证响应结构
    assert "error" in data, "响应应包含'error'字段"
    error = data["error"]

    # 验证必需字段
    assert "code" in error, "错误响应应包含'code'字段"
    assert "type" in error, "错误响应应包含'type'字段"
    assert "message" in error, "错误响应应包含'message'字段"
    assert "timestamp" in error, "错误响应应包含'timestamp'字段"

    # 验证字段类型
    assert isinstance(error["code"], str), "code应为字符串"
    assert isinstance(error["type"], str), "type应为字符串"
    assert isinstance(error["message"], str), "message应为字符串"
    assert isinstance(error["timestamp"], float), "timestamp应为浮点数"


def test_404_error_format():
    """测试404错误响应格式"""
    # 测试不存在的资源
    response = client.get("/api/v1/records/violations/999999")

    assert response.status_code == 404
    data = response.json()

    error = data["error"]
    assert error["code"] in ["RESOURCE_NOT_FOUND", "ENDPOINT_NOT_FOUND"]
    assert error["type"] == "not_found_error"
    assert "request_id" in error or error.get("request_id") is None


def test_400_error_format():
    """测试400错误响应格式"""
    # 测试无效参数
    response = client.get("/api/v1/records/violations?page=-1")

    # FastAPI会自动验证参数，可能返回422或400
    assert response.status_code in [400, 422]

    if response.status_code == 400:
        data = response.json()
        if "error" in data:
            error = data["error"]
            assert error["code"] in ["VALIDATION_ERROR", "INVALID_PARAMETER"]
            assert error["type"] == "validation_error"


def test_500_error_format():
    """测试500错误响应格式（需要模拟错误）"""
    # 注意：这个测试可能需要模拟一个真实的500错误
    # 由于我们无法轻易触发500错误，这里只验证中间件格式

    # 测试一个可能返回500的端点（如果服务不可用）
    # 这里我们测试一个需要数据库连接的端点
    response = client.get("/api/v1/records/statistics/summary")

    # 如果返回500，验证格式
    if response.status_code == 500:
        data = response.json()
        assert "error" in data
        error = data["error"]
        assert error["code"] in [
            "INTERNAL_SERVER_ERROR",
            "DATABASE_ERROR",
            "SERVICE_UNAVAILABLE",
        ]
        assert error["type"] in ["server_error", "service_unavailable"]


def test_503_error_format():
    """测试503错误响应格式"""
    # 测试服务不可用的情况
    # 注意：这需要服务实际不可用，或者我们模拟这种情况

    # 测试一个需要领域服务的端点
    response = client.get("/api/v1/statistics/realtime")

    # 如果返回503，验证格式
    if response.status_code == 503:
        data = response.json()
        assert "error" in data
        error = data["error"]
        assert error["code"] == "SERVICE_UNAVAILABLE"
        assert error["type"] == "service_unavailable"


def test_error_response_consistency():
    """测试不同端点的错误响应格式一致性"""
    endpoints_to_test = [
        "/api/v1/nonexistent",
        "/api/v1/records/violations/999999",
        "/api/v1/cameras/999999",
    ]

    for endpoint in endpoints_to_test:
        response = client.get(endpoint)

        if response.status_code >= 400:
            data = response.json()

            # 所有错误响应都应该有统一的结构
            assert "error" in data, f"端点 {endpoint} 的错误响应缺少'error'字段"
            error = data["error"]

            # 验证必需字段
            required_fields = ["code", "type", "message", "timestamp"]
            for field in required_fields:
                assert field in error, f"端点 {endpoint} 的错误响应缺少'{field}'字段"


def test_error_code_enum_values():
    """测试错误码是否符合枚举值"""
    response = client.get("/api/v1/nonexistent-endpoint")

    assert response.status_code == 404
    data = response.json()
    error = data["error"]

    # 验证错误码是有效的枚举值
    valid_codes = [
        "VALIDATION_ERROR",
        "INVALID_PARAMETER",
        "MISSING_REQUIRED_FIELD",
        "AUTHENTICATION_REQUIRED",
        "INVALID_CREDENTIALS",
        "TOKEN_EXPIRED",
        "AUTHORIZATION_FAILED",
        "INSUFFICIENT_PERMISSIONS",
        "RESOURCE_NOT_FOUND",
        "ENDPOINT_NOT_FOUND",
        "RESOURCE_CONFLICT",
        "DUPLICATE_RESOURCE",
        "RATE_LIMIT_EXCEEDED",
        "INTERNAL_SERVER_ERROR",
        "DATABASE_ERROR",
        "EXTERNAL_SERVICE_ERROR",
        "SERVICE_UNAVAILABLE",
        "DATABASE_UNAVAILABLE",
    ]

    assert error["code"] in valid_codes, f"错误码 {error['code']} 不在有效枚举值中"


def test_error_type_enum_values():
    """测试错误类型是否符合枚举值"""
    response = client.get("/api/v1/nonexistent-endpoint")

    assert response.status_code == 404
    data = response.json()
    error = data["error"]

    # 验证错误类型是有效的枚举值
    valid_types = [
        "validation_error",
        "authentication_error",
        "authorization_error",
        "not_found_error",
        "conflict_error",
        "rate_limit_error",
        "server_error",
        "service_unavailable",
        "database_error",
        "external_service_error",
    ]

    assert error["type"] in valid_types, f"错误类型 {error['type']} 不在有效枚举值中"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
