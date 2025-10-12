from google.api import annotations_pb2 as _annotations_pb2
from google.protobuf import timestamp_pb2 as _timestamp_pb2
from google.type import decimal_pb2 as _decimal_pb2
from google.type import interval_pb2 as _interval_pb2
from google.type import money_pb2 as _money_pb2
from grpc.tradeapi.v1 import side_pb2 as _side_pb2
from grpc.tradeapi.v1 import trade_pb2 as _trade_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class GetAccountRequest(_message.Message):
    __slots__ = ("account_id",)
    ACCOUNT_ID_FIELD_NUMBER: _ClassVar[int]
    account_id: str
    def __init__(self, account_id: _Optional[str] = ...) -> None: ...

class GetAccountResponse(_message.Message):
    __slots__ = ("account_id", "type", "status", "equity", "unrealized_profit", "positions", "cash", "portfolio_mc", "portfolio_mct", "portfolio_forts")
    ACCOUNT_ID_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    EQUITY_FIELD_NUMBER: _ClassVar[int]
    UNREALIZED_PROFIT_FIELD_NUMBER: _ClassVar[int]
    POSITIONS_FIELD_NUMBER: _ClassVar[int]
    CASH_FIELD_NUMBER: _ClassVar[int]
    PORTFOLIO_MC_FIELD_NUMBER: _ClassVar[int]
    PORTFOLIO_MCT_FIELD_NUMBER: _ClassVar[int]
    PORTFOLIO_FORTS_FIELD_NUMBER: _ClassVar[int]
    account_id: str
    type: str
    status: str
    equity: _decimal_pb2.Decimal
    unrealized_profit: _decimal_pb2.Decimal
    positions: _containers.RepeatedCompositeFieldContainer[Position]
    cash: _containers.RepeatedCompositeFieldContainer[_money_pb2.Money]
    portfolio_mc: MC
    portfolio_mct: MCT
    portfolio_forts: FORTS
    def __init__(self, account_id: _Optional[str] = ..., type: _Optional[str] = ..., status: _Optional[str] = ..., equity: _Optional[_Union[_decimal_pb2.Decimal, _Mapping]] = ..., unrealized_profit: _Optional[_Union[_decimal_pb2.Decimal, _Mapping]] = ..., positions: _Optional[_Iterable[_Union[Position, _Mapping]]] = ..., cash: _Optional[_Iterable[_Union[_money_pb2.Money, _Mapping]]] = ..., portfolio_mc: _Optional[_Union[MC, _Mapping]] = ..., portfolio_mct: _Optional[_Union[MCT, _Mapping]] = ..., portfolio_forts: _Optional[_Union[FORTS, _Mapping]] = ...) -> None: ...

class MC(_message.Message):
    __slots__ = ("available_cash", "initial_margin", "maintenance_margin")
    AVAILABLE_CASH_FIELD_NUMBER: _ClassVar[int]
    INITIAL_MARGIN_FIELD_NUMBER: _ClassVar[int]
    MAINTENANCE_MARGIN_FIELD_NUMBER: _ClassVar[int]
    available_cash: _decimal_pb2.Decimal
    initial_margin: _decimal_pb2.Decimal
    maintenance_margin: _decimal_pb2.Decimal
    def __init__(self, available_cash: _Optional[_Union[_decimal_pb2.Decimal, _Mapping]] = ..., initial_margin: _Optional[_Union[_decimal_pb2.Decimal, _Mapping]] = ..., maintenance_margin: _Optional[_Union[_decimal_pb2.Decimal, _Mapping]] = ...) -> None: ...

class MCT(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class FORTS(_message.Message):
    __slots__ = ("available_cash", "money_reserved")
    AVAILABLE_CASH_FIELD_NUMBER: _ClassVar[int]
    MONEY_RESERVED_FIELD_NUMBER: _ClassVar[int]
    available_cash: _decimal_pb2.Decimal
    money_reserved: _decimal_pb2.Decimal
    def __init__(self, available_cash: _Optional[_Union[_decimal_pb2.Decimal, _Mapping]] = ..., money_reserved: _Optional[_Union[_decimal_pb2.Decimal, _Mapping]] = ...) -> None: ...

class TradesRequest(_message.Message):
    __slots__ = ("account_id", "limit", "interval")
    ACCOUNT_ID_FIELD_NUMBER: _ClassVar[int]
    LIMIT_FIELD_NUMBER: _ClassVar[int]
    INTERVAL_FIELD_NUMBER: _ClassVar[int]
    account_id: str
    limit: int
    interval: _interval_pb2.Interval
    def __init__(self, account_id: _Optional[str] = ..., limit: _Optional[int] = ..., interval: _Optional[_Union[_interval_pb2.Interval, _Mapping]] = ...) -> None: ...

class TradesResponse(_message.Message):
    __slots__ = ("trades",)
    TRADES_FIELD_NUMBER: _ClassVar[int]
    trades: _containers.RepeatedCompositeFieldContainer[_trade_pb2.AccountTrade]
    def __init__(self, trades: _Optional[_Iterable[_Union[_trade_pb2.AccountTrade, _Mapping]]] = ...) -> None: ...

class TransactionsRequest(_message.Message):
    __slots__ = ("account_id", "limit", "interval")
    ACCOUNT_ID_FIELD_NUMBER: _ClassVar[int]
    LIMIT_FIELD_NUMBER: _ClassVar[int]
    INTERVAL_FIELD_NUMBER: _ClassVar[int]
    account_id: str
    limit: int
    interval: _interval_pb2.Interval
    def __init__(self, account_id: _Optional[str] = ..., limit: _Optional[int] = ..., interval: _Optional[_Union[_interval_pb2.Interval, _Mapping]] = ...) -> None: ...

class TransactionsResponse(_message.Message):
    __slots__ = ("transactions",)
    TRANSACTIONS_FIELD_NUMBER: _ClassVar[int]
    transactions: _containers.RepeatedCompositeFieldContainer[Transaction]
    def __init__(self, transactions: _Optional[_Iterable[_Union[Transaction, _Mapping]]] = ...) -> None: ...

class Position(_message.Message):
    __slots__ = ("symbol", "quantity", "average_price", "current_price", "maintenance_margin", "daily_pnl", "unrealized_pnl")
    SYMBOL_FIELD_NUMBER: _ClassVar[int]
    QUANTITY_FIELD_NUMBER: _ClassVar[int]
    AVERAGE_PRICE_FIELD_NUMBER: _ClassVar[int]
    CURRENT_PRICE_FIELD_NUMBER: _ClassVar[int]
    MAINTENANCE_MARGIN_FIELD_NUMBER: _ClassVar[int]
    DAILY_PNL_FIELD_NUMBER: _ClassVar[int]
    UNREALIZED_PNL_FIELD_NUMBER: _ClassVar[int]
    symbol: str
    quantity: _decimal_pb2.Decimal
    average_price: _decimal_pb2.Decimal
    current_price: _decimal_pb2.Decimal
    maintenance_margin: _decimal_pb2.Decimal
    daily_pnl: _decimal_pb2.Decimal
    unrealized_pnl: _decimal_pb2.Decimal
    def __init__(self, symbol: _Optional[str] = ..., quantity: _Optional[_Union[_decimal_pb2.Decimal, _Mapping]] = ..., average_price: _Optional[_Union[_decimal_pb2.Decimal, _Mapping]] = ..., current_price: _Optional[_Union[_decimal_pb2.Decimal, _Mapping]] = ..., maintenance_margin: _Optional[_Union[_decimal_pb2.Decimal, _Mapping]] = ..., daily_pnl: _Optional[_Union[_decimal_pb2.Decimal, _Mapping]] = ..., unrealized_pnl: _Optional[_Union[_decimal_pb2.Decimal, _Mapping]] = ...) -> None: ...

class Transaction(_message.Message):
    __slots__ = ("id", "category", "timestamp", "symbol", "change", "trade", "transaction_category", "transaction_name")
    class TransactionCategory(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = ()
        OTHERS: _ClassVar[Transaction.TransactionCategory]
        DEPOSIT: _ClassVar[Transaction.TransactionCategory]
        WITHDRAW: _ClassVar[Transaction.TransactionCategory]
        INCOME: _ClassVar[Transaction.TransactionCategory]
        COMMISSION: _ClassVar[Transaction.TransactionCategory]
        TAX: _ClassVar[Transaction.TransactionCategory]
        INHERITANCE: _ClassVar[Transaction.TransactionCategory]
        TRANSFER: _ClassVar[Transaction.TransactionCategory]
        CONTRACT_TERMINATION: _ClassVar[Transaction.TransactionCategory]
        OUTCOMES: _ClassVar[Transaction.TransactionCategory]
        FINE: _ClassVar[Transaction.TransactionCategory]
        LOAN: _ClassVar[Transaction.TransactionCategory]
    OTHERS: Transaction.TransactionCategory
    DEPOSIT: Transaction.TransactionCategory
    WITHDRAW: Transaction.TransactionCategory
    INCOME: Transaction.TransactionCategory
    COMMISSION: Transaction.TransactionCategory
    TAX: Transaction.TransactionCategory
    INHERITANCE: Transaction.TransactionCategory
    TRANSFER: Transaction.TransactionCategory
    CONTRACT_TERMINATION: Transaction.TransactionCategory
    OUTCOMES: Transaction.TransactionCategory
    FINE: Transaction.TransactionCategory
    LOAN: Transaction.TransactionCategory
    class Trade(_message.Message):
        __slots__ = ("size", "price", "accrued_interest")
        SIZE_FIELD_NUMBER: _ClassVar[int]
        PRICE_FIELD_NUMBER: _ClassVar[int]
        ACCRUED_INTEREST_FIELD_NUMBER: _ClassVar[int]
        size: _decimal_pb2.Decimal
        price: _decimal_pb2.Decimal
        accrued_interest: _decimal_pb2.Decimal
        def __init__(self, size: _Optional[_Union[_decimal_pb2.Decimal, _Mapping]] = ..., price: _Optional[_Union[_decimal_pb2.Decimal, _Mapping]] = ..., accrued_interest: _Optional[_Union[_decimal_pb2.Decimal, _Mapping]] = ...) -> None: ...
    ID_FIELD_NUMBER: _ClassVar[int]
    CATEGORY_FIELD_NUMBER: _ClassVar[int]
    TIMESTAMP_FIELD_NUMBER: _ClassVar[int]
    SYMBOL_FIELD_NUMBER: _ClassVar[int]
    CHANGE_FIELD_NUMBER: _ClassVar[int]
    TRADE_FIELD_NUMBER: _ClassVar[int]
    TRANSACTION_CATEGORY_FIELD_NUMBER: _ClassVar[int]
    TRANSACTION_NAME_FIELD_NUMBER: _ClassVar[int]
    id: str
    category: str
    timestamp: _timestamp_pb2.Timestamp
    symbol: str
    change: _money_pb2.Money
    trade: Transaction.Trade
    transaction_category: Transaction.TransactionCategory
    transaction_name: str
    def __init__(self, id: _Optional[str] = ..., category: _Optional[str] = ..., timestamp: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., symbol: _Optional[str] = ..., change: _Optional[_Union[_money_pb2.Money, _Mapping]] = ..., trade: _Optional[_Union[Transaction.Trade, _Mapping]] = ..., transaction_category: _Optional[_Union[Transaction.TransactionCategory, str]] = ..., transaction_name: _Optional[str] = ...) -> None: ...
