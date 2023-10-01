from sanic_openapi import openapi


class BaseApiModel:

    _uri = ""
    _name = ""
    _method: str = "GET"
    _summary = ""
    _description = ""
    _request_content_type = "application/json"
    _response_content_type = "application/json"

    @classmethod
    def uri(cls):
        return cls._uri

    @classmethod
    def name(cls):
        return cls._name

    @classmethod
    def http_method(cls):
        return cls._method

    @classmethod
    def summary(cls):
        return cls._summary

    @classmethod
    def description(cls):
        return cls._description

    @classmethod
    def request_content_type(cls):
        return cls._request_content_type

    @classmethod
    def response_content_type(cls):
        return cls._response_content_type

    class RequestBodyOpenApiModel:
        """
        Represents the request body model
        """

    class RequestParamsOpenApiModel:
        """
        Represents the request query param model
        """

    class ResponseBodyOpenApiModel:
        """
        Represents the response body model
        """


class File:
    url = openapi.String(
        descritpion="File url",
        example="https://1mg-odin-production.s3.ap-south-1.amazonaws.com/upload/sales_orders/42550349/6f55151e-adb5-4171-8fe2-5eb6599eafb7.pdf",
        required=True,
    )
    filename = openapi.String(
        descritpion="File name", example="report.pdf", required=True
    )
