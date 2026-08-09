from pathlib import Path
import runpy
from unittest.mock import Mock

import pytest

import journal.main as main_module
from journal import menu as menu_module
from journal import storage as storage_module


def test_main_loads_data_and_runs_menu_in_order(monkeypatch):
    events = []
    trades = [{"symbol": "MES"}]
    account = {"starting_balance": 25000.0}

    def fake_load_trades():
        events.append("load_trades")
        return trades

    def fake_load_account():
        events.append("load_account")
        return account

    def fake_run_menu(received_trades, received_account):
        events.append("run_menu")
        assert received_trades is trades
        assert received_account is account

    monkeypatch.setattr(
        main_module,
        "load_trades",
        fake_load_trades,
    )
    monkeypatch.setattr(
        main_module,
        "load_account",
        fake_load_account,
    )
    monkeypatch.setattr(
        main_module,
        "run_menu",
        fake_run_menu,
    )

    assert main_module.main() is None
    assert events == [
        "load_trades",
        "load_account",
        "run_menu",
    ]


def test_main_passes_empty_loaded_data_to_menu(monkeypatch):
    trades = []
    account = {}
    run_menu = Mock()

    monkeypatch.setattr(
        main_module,
        "load_trades",
        Mock(return_value=trades),
    )
    monkeypatch.setattr(
        main_module,
        "load_account",
        Mock(return_value=account),
    )
    monkeypatch.setattr(
        main_module,
        "run_menu",
        run_menu,
    )

    main_module.main()

    run_menu.assert_called_once_with(trades, account)


def test_main_stops_when_loading_trades_fails(monkeypatch):
    error = OSError("trades could not be loaded")
    load_account = Mock()
    run_menu = Mock()

    monkeypatch.setattr(
        main_module,
        "load_trades",
        Mock(side_effect=error),
    )
    monkeypatch.setattr(
        main_module,
        "load_account",
        load_account,
    )
    monkeypatch.setattr(
        main_module,
        "run_menu",
        run_menu,
    )

    with pytest.raises(OSError) as exc_info:
        main_module.main()

    assert exc_info.value is error
    load_account.assert_not_called()
    run_menu.assert_not_called()


def test_main_stops_when_loading_account_fails(monkeypatch):
    trades = [{"symbol": "MNQ"}]
    error = OSError("account could not be loaded")
    load_trades = Mock(return_value=trades)
    run_menu = Mock()

    monkeypatch.setattr(
        main_module,
        "load_trades",
        load_trades,
    )
    monkeypatch.setattr(
        main_module,
        "load_account",
        Mock(side_effect=error),
    )
    monkeypatch.setattr(
        main_module,
        "run_menu",
        run_menu,
    )

    with pytest.raises(OSError) as exc_info:
        main_module.main()

    assert exc_info.value is error
    load_trades.assert_called_once_with()
    run_menu.assert_not_called()


def test_main_propagates_menu_errors(monkeypatch):
    trades = [{"symbol": "EUR/USD"}]
    account = {"account_currency": "CAD"}
    error = RuntimeError("menu stopped")
    run_menu = Mock(side_effect=error)

    monkeypatch.setattr(
        main_module,
        "load_trades",
        Mock(return_value=trades),
    )
    monkeypatch.setattr(
        main_module,
        "load_account",
        Mock(return_value=account),
    )
    monkeypatch.setattr(
        main_module,
        "run_menu",
        run_menu,
    )

    with pytest.raises(RuntimeError) as exc_info:
        main_module.main()

    assert exc_info.value is error
    run_menu.assert_called_once_with(trades, account)


def test_importing_main_file_does_not_start_application(
    monkeypatch,
):
    load_trades = Mock()
    load_account = Mock()
    run_menu = Mock()

    monkeypatch.setattr(
        storage_module,
        "load_trades",
        load_trades,
    )
    monkeypatch.setattr(
        storage_module,
        "load_account",
        load_account,
    )
    monkeypatch.setattr(
        menu_module,
        "run_menu",
        run_menu,
    )

    runpy.run_path(
        str(Path(main_module.__file__)),
        run_name="journal.main_import_test",
    )

    load_trades.assert_not_called()
    load_account.assert_not_called()
    run_menu.assert_not_called()


def test_running_main_file_executes_startup(monkeypatch):
    trades = [{"symbol": "MGC"}]
    account = {"starting_balance": 10000.0}
    load_trades = Mock(return_value=trades)
    load_account = Mock(return_value=account)
    run_menu = Mock()

    monkeypatch.setattr(
        storage_module,
        "load_trades",
        load_trades,
    )
    monkeypatch.setattr(
        storage_module,
        "load_account",
        load_account,
    )
    monkeypatch.setattr(
        menu_module,
        "run_menu",
        run_menu,
    )

    runpy.run_path(
        str(Path(main_module.__file__)),
        run_name="__main__",
    )

    load_trades.assert_called_once_with()
    load_account.assert_called_once_with()
    run_menu.assert_called_once_with(trades, account)


def test_package_launcher_calls_main(monkeypatch):
    main = Mock()
    launcher_path = Path(main_module.__file__).with_name(
        "__main__.py"
    )

    monkeypatch.setattr(main_module, "main", main)

    runpy.run_path(
        str(launcher_path),
        run_name="__main__",
    )

    main.assert_called_once_with()
    