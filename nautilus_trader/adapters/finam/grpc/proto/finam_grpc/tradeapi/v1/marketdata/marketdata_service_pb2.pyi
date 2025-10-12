from google.api import annotations_pb2 as _annotations_pb2
from google.protobuf import timestamp_pb2 as _timestamp_pb2
from google.type import decimal_pb2 as _decimal_pb2
from google.type import interval_pb2 as _interval_pb2
from grpc.tradeapi.v1 import side_pb2 as _side_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class TimeFrame(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    TIME_FRAME_UNSPECIFIED: _ClassVar[TimeFrame]
    TIME_FRAME_M1: _ClassVar[TimeFrame]
    TIME_FRAME_M5: _ClassVar[TimeFrame]
    TIME_FRAME_M15: _ClassVar[TimeFrame]
    TIME_FRAME_M30: _ClassVar[TimeFrame]
    TIME_FRAME_H1: _ClassVar[TimeFrame]
    TIME_FRAME_H2: _ClassVar[TimeFrame]
    TIME_FRAME_H4: _ClassVar[TimeFrame]
    TIME_FRAME_H8: _ClassVar[TimeFrame]
    TIME_FRAME_D: _ClassVar[TimeFrame]
    TIME_FRAME_W: _ClassVar[TimeFrame]
    TIME_FRAME_MN: _ClassVar[TimeFrame]
    TIME_FRAME_QR: _ClassVar[TimeFrame]
TIME_FRAME_UNSPECIFIED: TimeFrame
TIME_FRAME_M1: TimeFrame
TIME_FRAME_M5: TimeFrame
TIME_FRAME_M15: TimeFrame
TIME_FRAME_M30: TimeFrame
TIME_FRAME_H1: TimeFrame
TIME_FRAME_H2: TimeFrame
TIME_FRAME_H4: TimeFrame
TIME_FRAME_H8: TimeFrame
TIME_FRAME_D: TimeFrame
TIME_FRAME_W: TimeFrame
TIME_FRAME_MN: TimeFrame
TIME_FRAME_QR: TimeFrame

class BarsRequest(_message.Message):
    __slots__ = ("symbol", "timeframe", "interval")
    SYMBOL_FIELD_NUMBER: _ClassVar[int]
    TIMEFRAME_FIELD_NUMBER: _ClassVar[int]
    INTERVAL_FIELD_NUMBER: _ClassVar[int]
    symbol: str
    timeframe: TimeFrame
    interval: _interval_pb2.Interval
    def __init__(self, symbol: _Optional[str] = ..., timeframe: _Optional[_Union[TimeFrame, str]] = ..., interval: _Optional[_Union[_interval_pb2.Interval, _Mapping]] = ...) -> None: ...

class BarsResponse(_message.Message):
    __slots__ = ("symbol", "bars")
    SYMBOL_FIELD_NUMBER: _ClassVar[int]
    BARS_FIELD_NUMBER: _ClassVar[int]
    symbol: str
    bars: _containers.RepeatedCompositeFieldContainer[Bar]
    def __init__(self, symbol: _Optional[str] = ..., bars: _Optional[_Iterable[_Union[Bar, _Mapping]]] = ...) -> None: ...

class QuoteRequest(_message.Message):
    __slots__ = ("symbol",)
    SYMBOL_FIELD_NUMBER: _ClassVar[int]
    symbol: str
    def __init__(self, symbol: _Optional[str] = ...) -> None: ...

class QuoteResponse(_message.Message):
    __slots__ = ("symbol", "quote")
    SYMBOL_FIELD_NUMBER: _ClassVar[int]
    QUOTE_FIELD_NUMBER: _ClassVar[int]
    symbol: str
    quote: Quote
    def __init__(self, symbol: _Optional[str] = ..., quote: _Optional[_Union[Quote, _Mapping]] = ...) -> None: ...

class OrderBookRequest(_message.Message):
    __slots__ = ("symbol",)
    SYMBOL_FIELD_NUMBER: _ClassVar[int]
    symbol: str
    def __init__(self, symbol: _Optional[str] = ...) -> None: ...

class OrderBookResponse(_message.Message):
    __slots__ = ("symbol", "orderbook")
    SYMBOL_FIELD_NUMBER: _ClassVar[int]
    ORDERBOOK_FIELD_NUMBER: _ClassVar[int]
    symbol: str
    orderbook: OrderBook
    def __init__(self, symbol: _Optional[str] = ..., orderbook: _Optional[_Union[OrderBook, _Mapping]] = ...) -> None: ...

class LatestTradesRequest(_message.Message):
    __slots__ = ("symbol",)
    SYMBOL_FIELD_NUMBER: _ClassVar[int]
    symbol: str
    def __init__(self, symbol: _Optional[str] = ...) -> None: ...

class LatestTradesResponse(_message.Message):
    __slots__ = ("symbol", "trades")
    SYMBOL_FIELD_NUMBER: _ClassVar[int]
    TRADES_FIELD_NUMBER: _ClassVar[int]
    symbol: str
    trades: _containers.RepeatedCompositeFieldContainer[Trade]
    def __init__(self, symbol: _Optional[str] = ..., trades: _Optional[_Iterable[_Union[Trade, _Mapping]]] = ...) -> None: ...

class SubscribeQuoteRequest(_message.Message):
    __slots__ = ("symbols",)
    SYMBOLS_FIELD_NUMBER: _ClassVar[int]
    symbols: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, symbols: _Optional[_Iterable[str]] = ...) -> None: ...

class SubscribeQuoteResponse(_message.Message):
    __slots__ = ("quote", "error")
    QUOTE_FIELD_NUMBER: _ClassVar[int]
    ERROR_FIELD_NUMBER: _ClassVar[int]
    quote: _containers.RepeatedCompositeFieldContainer[Quote]
    error: StreamError
    def __init__(self, quote: _Optional[_Iterable[_Union[Quote, _Mapping]]] = ..., error: _Optional[_Union[StreamError, _Mapping]] = ...) -> None: ...

class SubscribeOrderBookRequest(_message.Message):
    __slots__ = ("symbol",)
    SYMBOL_FIELD_NUMBER: _ClassVar[int]
    symbol: str
    def __init__(self, symbol: _Optional[str] = ...) -> None: ...

class SubscribeOrderBookResponse(_message.Message):
    __slots__ = ("order_book",)
    ORDER_BOOK_FIELD_NUMBER: _ClassVar[int]
    order_book: _containers.RepeatedCompositeFieldContainer[StreamOrderBook]
    def __init__(self, order_book: _Optional[_Iterable[_Union[StreamOrderBook, _Mapping]]] = ...) -> None: ...

class SubscribeBarsRequest(_message.Message):
    __slots__ = ("symbol", "timeframe")
    SYMBOL_FIELD_NUMBER: _ClassVar[int]
    TIMEFRAME_FIELD_NUMBER: _ClassVar[int]
    symbol: str
    timeframe: TimeFrame
    def __init__(self, symbol: _Optional[str] = ..., timeframe: _Optional[_Union[TimeFrame, str]] = ...) -> None: ...

class SubscribeBarsResponse(_message.Message):
    __slots__ = ("symbol", "bars")
    SYMBOL_FIELD_NUMBER: _ClassVar[int]
    BARS_FIELD_NUMBER: _ClassVar[int]
    symbol: str
    bars: _containers.RepeatedCompositeFieldContainer[Bar]
    def __init__(self, symbol: _Optional[str] = ..., bars: _Optional[_Iterable[_Union[Bar, _Mapping]]] = ...) -> None: ...

class Bar(_message.Message):
    __slots__ = ("timestamp", "open", "high", "low", "close", "volume")
    TIMESTAMP_FIELD_NUMBER: _ClassVar[int]
    OPEN_FIELD_NUMBER: _ClassVar[int]
    HIGH_FIELD_NUMBER: _ClassVar[int]
    LOW_FIELD_NUMBER: _ClassVar[int]
    CLOSE_FIELD_NUMBER: _ClassVar[int]
    VOLUME_FIELD_NUMBER: _ClassVar[int]
    timestamp: _timestamp_pb2.Timestamp
    open: _decimal_pb2.Decimal
    high: _decimal_pb2.Decimal
    low: _decimal_pb2.Decimal
    close: _decimal_pb2.Decimal
    volume: _decimal_pb2.Decimal
    def __init__(self, timestamp: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., open: _Optional[_Union[_decimal_pb2.Decimal, _Mapping]] = ..., high: _Optional[_Union[_decimal_pb2.Decimal, _Mapping]] = ..., low: _Optional[_Union[_decimal_pb2.Decimal, _Mapping]] = ..., close: _Optional[_Union[_decimal_pb2.Decimal, _Mapping]] = ..., volume: _Optional[_Union[_decimal_pb2.Decimal, _Mapping]] = ...) -> None: ...

class Quote(_message.Message):
    __slots__ = ("symbol", "timestamp", "ask", "ask_size", "bid", "bid_size", "last", "last_size", "volume", "turnover", "open", "high", "low", "close", "change", "option")
    class Option(_message.Message):
        __slots__ = ("open_interest", "implied_volatility", "theoretical_price", "delta", "gamma", "theta", "vega", "rho")
        OPEN_INTEREST_FIELD_NUMBER: _ClassVar[int]
        IMPLIED_VOLATILITY_FIELD_NUMBER: _ClassVar[int]
        THEORETICAL_PRICE_FIELD_NUMBER: _ClassVar[int]
        DELTA_FIELD_NUMBER: _ClassVar[int]
        GAMMA_FIELD_NUMBER: _ClassVar[int]
        THETA_FIELD_NUMBER: _ClassVar[int]
        VEGA_FIELD_NUMBER: _ClassVar[int]
        RHO_FIELD_NUMBER: _ClassVar[int]
        open_interest: _decimal_pb2.Decimal
        implied_volatility: _decimal_pb2.Decimal
        theoretical_price: _decimal_pb2.Decimal
        delta: _decimal_pb2.Decimal
        gamma: _decimal_pb2.Decimal
        theta: _decimal_pb2.Decimal
        vega: _decimal_pb2.Decimal
        rho: _decimal_pb2.Decimal
        def __init__(self, open_interest: _Optional[_Union[_decimal_pb2.Decimal, _Mapping]] = ..., implied_volatility: _Optional[_Union[_decimal_pb2.Decimal, _Mapping]] = ..., theoretical_price: _Optional[_Union[_decimal_pb2.Decimal, _Mapping]] = ..., delta: _Optional[_Union[_decimal_pb2.Decimal, _Mapping]] = ..., gamma: _Optional[_Union[_decimal_pb2.Decimal, _Mapping]] = ..., theta: _Optional[_Union[_decimal_pb2.Decimal, _Mapping]] = ..., vega: _Optional[_Union[_decimal_pb2.Decimal, _Mapping]] = ..., rho: _Optional[_Union[_decimal_pb2.Decimal, _Mapping]] = ...) -> None: ...
    SYMBOL_FIELD_NUMBER: _ClassVar[int]
    TIMESTAMP_FIELD_NUMBER: _ClassVar[int]
    ASK_FIELD_NUMBER: _ClassVar[int]
    ASK_SIZE_FIELD_NUMBER: _ClassVar[int]
    BID_FIELD_NUMBER: _ClassVar[int]
    BID_SIZE_FIELD_NUMBER: _ClassVar[int]
    LAST_FIELD_NUMBER: _ClassVar[int]
    LAST_SIZE_FIELD_NUMBER: _ClassVar[int]
    VOLUME_FIELD_NUMBER: _ClassVar[int]
    TURNOVER_FIELD_NUMBER: _ClassVar[int]
    OPEN_FIELD_NUMBER: _ClassVar[int]
    HIGH_FIELD_NUMBER: _ClassVar[int]
    LOW_FIELD_NUMBER: _ClassVar[int]
    CLOSE_FIELD_NUMBER: _ClassVar[int]
    CHANGE_FIELD_NUMBER: _ClassVar[int]
    OPTION_FIELD_NUMBER: _ClassVar[int]
    symbol: str
    timestamp: _timestamp_pb2.Timestamp
    ask: _decimal_pb2.Decimal
    ask_size: _decimal_pb2.Decimal
    bid: _decimal_pb2.Decimal
    bid_size: _decimal_pb2.Decimal
    last: _decimal_pb2.Decimal
    last_size: _decimal_pb2.Decimal
    volume: _decimal_pb2.Decimal
    turnover: _decimal_pb2.Decimal
    open: _decimal_pb2.Decimal
    high: _decimal_pb2.Decimal
    low: _decimal_pb2.Decimal
    close: _decimal_pb2.Decimal
    change: _decimal_pb2.Decimal
    option: Quote.Option
    def __init__(self, symbol: _Optional[str] = ..., timestamp: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., ask: _Optional[_Union[_decimal_pb2.Decimal, _Mapping]] = ..., ask_size: _Optional[_Union[_decimal_pb2.Decimal, _Mapping]] = ..., bid: _Optional[_Union[_decimal_pb2.Decimal, _Mapping]] = ..., bid_size: _Optional[_Union[_decimal_pb2.Decimal, _Mapping]] = ..., last: _Optional[_Union[_decimal_pb2.Decimal, _Mapping]] = ..., last_size: _Optional[_Union[_decimal_pb2.Decimal, _Mapping]] = ..., volume: _Optional[_Union[_decimal_pb2.Decimal, _Mapping]] = ..., turnover: _Optional[_Union[_decimal_pb2.Decimal, _Mapping]] = ..., open: _Optional[_Union[_decimal_pb2.Decimal, _Mapping]] = ..., high: _Optional[_Union[_decimal_pb2.Decimal, _Mapping]] = ..., low: _Optional[_Union[_decimal_pb2.Decimal, _Mapping]] = ..., close: _Optional[_Union[_decimal_pb2.Decimal, _Mapping]] = ..., change: _Optional[_Union[_decimal_pb2.Decimal, _Mapping]] = ..., option: _Optional[_Union[Quote.Option, _Mapping]] = ...) -> None: ...

class OrderBook(_message.Message):
    __slots__ = ("rows",)
    class Row(_message.Message):
        __slots__ = ("price", "sell_size", "buy_size", "action", "mpid", "timestamp")
        class Action(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
            __slots__ = ()
            ACTION_UNSPECIFIED: _ClassVar[OrderBook.Row.Action]
            ACTION_REMOVE: _ClassVar[OrderBook.Row.Action]
            ACTION_ADD: _ClassVar[OrderBook.Row.Action]
            ACTION_UPDATE: _ClassVar[OrderBook.Row.Action]
        ACTION_UNSPECIFIED: OrderBook.Row.Action
        ACTION_REMOVE: OrderBook.Row.Action
        ACTION_ADD: OrderBook.Row.Action
        ACTION_UPDATE: OrderBook.Row.Action
        PRICE_FIELD_NUMBER: _ClassVar[int]
        SELL_SIZE_FIELD_NUMBER: _ClassVar[int]
        BUY_SIZE_FIELD_NUMBER: _ClassVar[int]
        ACTION_FIELD_NUMBER: _ClassVar[int]
        MPID_FIELD_NUMBER: _ClassVar[int]
        TIMESTAMP_FIELD_NUMBER: _ClassVar[int]
        price: _decimal_pb2.Decimal
        sell_size: _decimal_pb2.Decimal
        buy_size: _decimal_pb2.Decimal
        action: OrderBook.Row.Action
        mpid: str
        timestamp: _timestamp_pb2.Timestamp
        def __init__(self, price: _Optional[_Union[_decimal_pb2.Decimal, _Mapping]] = ..., sell_size: _Optional[_Union[_decimal_pb2.Decimal, _Mapping]] = ..., buy_size: _Optional[_Union[_decimal_pb2.Decimal, _Mapping]] = ..., action: _Optional[_Union[OrderBook.Row.Action, str]] = ..., mpid: _Optional[str] = ..., timestamp: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ...) -> None: ...
    ROWS_FIELD_NUMBER: _ClassVar[int]
    rows: _containers.RepeatedCompositeFieldContainer[OrderBook.Row]
    def __init__(self, rows: _Optional[_Iterable[_Union[OrderBook.Row, _Mapping]]] = ...) -> None: ...

class Trade(_message.Message):
    __slots__ = ("trade_id", "mpid", "timestamp", "price", "size", "side")
    TRADE_ID_FIELD_NUMBER: _ClassVar[int]
    MPID_FIELD_NUMBER: _ClassVar[int]
    TIMESTAMP_FIELD_NUMBER: _ClassVar[int]
    PRICE_FIELD_NUMBER: _ClassVar[int]
    SIZE_FIELD_NUMBER: _ClassVar[int]
    SIDE_FIELD_NUMBER: _ClassVar[int]
    trade_id: str
    mpid: str
    timestamp: _timestamp_pb2.Timestamp
    price: _decimal_pb2.Decimal
    size: _decimal_pb2.Decimal
    side: _side_pb2.Side
    def __init__(self, trade_id: _Optional[str] = ..., mpid: _Optional[str] = ..., timestamp: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., price: _Optional[_Union[_decimal_pb2.Decimal, _Mapping]] = ..., size: _Optional[_Union[_decimal_pb2.Decimal, _Mapping]] = ..., side: _Optional[_Union[_side_pb2.Side, str]] = ...) -> None: ...

class StreamError(_message.Message):
    __slots__ = ("code", "description")
    CODE_FIELD_NUMBER: _ClassVar[int]
    DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    code: int
    description: str
    def __init__(self, code: _Optional[int] = ..., description: _Optional[str] = ...) -> None: ...

class StreamOrderBook(_message.Message):
    __slots__ = ("symbol", "rows")
    class Row(_message.Message):
        __slots__ = ("price", "sell_size", "buy_size", "action", "mpid", "timestamp")
        class Action(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
            __slots__ = ()
            ACTION_UNSPECIFIED: _ClassVar[StreamOrderBook.Row.Action]
            ACTION_REMOVE: _ClassVar[StreamOrderBook.Row.Action]
            ACTION_ADD: _ClassVar[StreamOrderBook.Row.Action]
            ACTION_UPDATE: _ClassVar[StreamOrderBook.Row.Action]
        ACTION_UNSPECIFIED: StreamOrderBook.Row.Action
        ACTION_REMOVE: StreamOrderBook.Row.Action
        ACTION_ADD: StreamOrderBook.Row.Action
        ACTION_UPDATE: StreamOrderBook.Row.Action
        PRICE_FIELD_NUMBER: _ClassVar[int]
        SELL_SIZE_FIELD_NUMBER: _ClassVar[int]
        BUY_SIZE_FIELD_NUMBER: _ClassVar[int]
        ACTION_FIELD_NUMBER: _ClassVar[int]
        MPID_FIELD_NUMBER: _ClassVar[int]
        TIMESTAMP_FIELD_NUMBER: _ClassVar[int]
        price: _decimal_pb2.Decimal
        sell_size: _decimal_pb2.Decimal
        buy_size: _decimal_pb2.Decimal
        action: StreamOrderBook.Row.Action
        mpid: str
        timestamp: _timestamp_pb2.Timestamp
        def __init__(self, price: _Optional[_Union[_decimal_pb2.Decimal, _Mapping]] = ..., sell_size: _Optional[_Union[_decimal_pb2.Decimal, _Mapping]] = ..., buy_size: _Optional[_Union[_decimal_pb2.Decimal, _Mapping]] = ..., action: _Optional[_Union[StreamOrderBook.Row.Action, str]] = ..., mpid: _Optional[str] = ..., timestamp: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ...) -> None: ...
    SYMBOL_FIELD_NUMBER: _ClassVar[int]
    ROWS_FIELD_NUMBER: _ClassVar[int]
    symbol: str
    rows: _containers.RepeatedCompositeFieldContainer[StreamOrderBook.Row]
    def __init__(self, symbol: _Optional[str] = ..., rows: _Optional[_Iterable[_Union[StreamOrderBook.Row, _Mapping]]] = ...) -> None: ...

class SubscribeLatestTradesRequest(_message.Message):
    __slots__ = ("symbol",)
    SYMBOL_FIELD_NUMBER: _ClassVar[int]
    symbol: str
    def __init__(self, symbol: _Optional[str] = ...) -> None: ...

class SubscribeLatestTradesResponse(_message.Message):
    __slots__ = ("symbol", "trades")
    SYMBOL_FIELD_NUMBER: _ClassVar[int]
    TRADES_FIELD_NUMBER: _ClassVar[int]
    symbol: str
    trades: _containers.RepeatedCompositeFieldContainer[Trade]
    def __init__(self, symbol: _Optional[str] = ..., trades: _Optional[_Iterable[_Union[Trade, _Mapping]]] = ...) -> None: ...
