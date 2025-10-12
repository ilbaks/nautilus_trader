from google.protobuf import timestamp_pb2 as _timestamp_pb2
from google.type import decimal_pb2 as _decimal_pb2
from grpc.tradeapi.v1 import side_pb2 as _side_pb2
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class AccountTrade(_message.Message):
    __slots__ = ("trade_id", "symbol", "price", "size", "side", "timestamp", "order_id", "account_id")
    TRADE_ID_FIELD_NUMBER: _ClassVar[int]
    SYMBOL_FIELD_NUMBER: _ClassVar[int]
    PRICE_FIELD_NUMBER: _ClassVar[int]
    SIZE_FIELD_NUMBER: _ClassVar[int]
    SIDE_FIELD_NUMBER: _ClassVar[int]
    TIMESTAMP_FIELD_NUMBER: _ClassVar[int]
    ORDER_ID_FIELD_NUMBER: _ClassVar[int]
    ACCOUNT_ID_FIELD_NUMBER: _ClassVar[int]
    trade_id: str
    symbol: str
    price: _decimal_pb2.Decimal
    size: _decimal_pb2.Decimal
    side: _side_pb2.Side
    timestamp: _timestamp_pb2.Timestamp
    order_id: str
    account_id: str
    def __init__(self, trade_id: _Optional[str] = ..., symbol: _Optional[str] = ..., price: _Optional[_Union[_decimal_pb2.Decimal, _Mapping]] = ..., size: _Optional[_Union[_decimal_pb2.Decimal, _Mapping]] = ..., side: _Optional[_Union[_side_pb2.Side, str]] = ..., timestamp: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., order_id: _Optional[str] = ..., account_id: _Optional[str] = ...) -> None: ...
