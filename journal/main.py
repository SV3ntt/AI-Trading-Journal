from journal.storage import load_account, load_trades
from journal.menu import run_menu


def main():
      trades = load_trades()
      account = load_account()
      run_menu(trades, account)


if __name__ == "__main__":
      main()
