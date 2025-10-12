from google.api import annotations_pb2 as _annotations_pb2
from google.protobuf import timestamp_pb2 as _timestamp_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class AuthRequest(_message.Message):
    __slots__ = ("secret",)
    SECRET_FIELD_NUMBER: _ClassVar[int]
    secret: str
    def __init__(self, secret: _Optional[str] = ...) -> None: ...

class AuthResponse(_message.Message):
    __slots__ = ("token",)
    TOKEN_FIELD_NUMBER: _ClassVar[int]
    token: str
    def __init__(self, token: _Optional[str] = ...) -> None: ...

class TokenDetailsRequest(_message.Message):
    __slots__ = ("token",)
    TOKEN_FIELD_NUMBER: _ClassVar[int]
    token: str
    def __init__(self, token: _Optional[str] = ...) -> None: ...

class TokenDetailsResponse(_message.Message):
    __slots__ = ("created_at", "expires_at", "md_permissions", "account_ids", "readonly")
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    EXPIRES_AT_FIELD_NUMBER: _ClassVar[int]
    MD_PERMISSIONS_FIELD_NUMBER: _ClassVar[int]
    ACCOUNT_IDS_FIELD_NUMBER: _ClassVar[int]
    READONLY_FIELD_NUMBER: _ClassVar[int]
    created_at: _timestamp_pb2.Timestamp
    expires_at: _timestamp_pb2.Timestamp
    md_permissions: _containers.RepeatedCompositeFieldContainer[MDPermission]
    account_ids: _containers.RepeatedScalarFieldContainer[str]
    readonly: bool
    def __init__(self, created_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., expires_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., md_permissions: _Optional[_Iterable[_Union[MDPermission, _Mapping]]] = ..., account_ids: _Optional[_Iterable[str]] = ..., readonly: bool = ...) -> None: ...

class MDPermission(_message.Message):
    __slots__ = ("quote_level", "delay_minutes", "mic", "country", "continent", "worldwide")
    class QuoteLevel(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = ()
        QUOTE_LEVEL_UNSPECIFIED: _ClassVar[MDPermission.QuoteLevel]
        QUOTE_LEVEL_LAST_PRICE: _ClassVar[MDPermission.QuoteLevel]
        QUOTE_LEVEL_BEST_BID_OFFER: _ClassVar[MDPermission.QuoteLevel]
        QUOTE_LEVEL_DEPTH_OF_MARKET: _ClassVar[MDPermission.QuoteLevel]
        QUOTE_LEVEL_DEPTH_OF_BOOK: _ClassVar[MDPermission.QuoteLevel]
        QUOTE_LEVEL_ACCESS_FORBIDDEN: _ClassVar[MDPermission.QuoteLevel]
    QUOTE_LEVEL_UNSPECIFIED: MDPermission.QuoteLevel
    QUOTE_LEVEL_LAST_PRICE: MDPermission.QuoteLevel
    QUOTE_LEVEL_BEST_BID_OFFER: MDPermission.QuoteLevel
    QUOTE_LEVEL_DEPTH_OF_MARKET: MDPermission.QuoteLevel
    QUOTE_LEVEL_DEPTH_OF_BOOK: MDPermission.QuoteLevel
    QUOTE_LEVEL_ACCESS_FORBIDDEN: MDPermission.QuoteLevel
    QUOTE_LEVEL_FIELD_NUMBER: _ClassVar[int]
    DELAY_MINUTES_FIELD_NUMBER: _ClassVar[int]
    MIC_FIELD_NUMBER: _ClassVar[int]
    COUNTRY_FIELD_NUMBER: _ClassVar[int]
    CONTINENT_FIELD_NUMBER: _ClassVar[int]
    WORLDWIDE_FIELD_NUMBER: _ClassVar[int]
    quote_level: MDPermission.QuoteLevel
    delay_minutes: int
    mic: str
    country: str
    continent: str
    worldwide: bool
    def __init__(self, quote_level: _Optional[_Union[MDPermission.QuoteLevel, str]] = ..., delay_minutes: _Optional[int] = ..., mic: _Optional[str] = ..., country: _Optional[str] = ..., continent: _Optional[str] = ..., worldwide: bool = ...) -> None: ...

class SubscribeJwtRenewalRequest(_message.Message):
    __slots__ = ("secret",)
    SECRET_FIELD_NUMBER: _ClassVar[int]
    secret: str
    def __init__(self, secret: _Optional[str] = ...) -> None: ...

class SubscribeJwtRenewalResponse(_message.Message):
    __slots__ = ("token",)
    TOKEN_FIELD_NUMBER: _ClassVar[int]
    token: str
    def __init__(self, token: _Optional[str] = ...) -> None: ...
