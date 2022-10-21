from typing import Union
from loguru import logger

import bs4
import pandas as pd
import requests
import sys
from datetime import date
from tabulate import tabulate


class BEAUTIFUL_SOUP:
    def __init__(self, url: str) -> None:
        self.url = url

    def request(self) -> Union[str, requests.Response]:

        try:
            request: requests.Response = requests.get(self.url)
        except Exception as e:
            return str(e)

        return request

    @staticmethod
    def get_data(
        request: requests.Response, query_elements: list[str]
    ) -> bs4.ResultSet:

        html_raw = bs4.BeautifulSoup(request.text, "lxml")
        html_data = html_raw.find_all(
            query_elements[0], {query_elements[1]: query_elements[2]}
        )
        return html_data


def get_top_data(category: str) -> tuple[list[str], pd.DataFrame]:

    # Initiate soup class instance.
    soup_ticker: BEAUTIFUL_SOUP = BEAUTIFUL_SOUP(
        url=f"https://www.tradingview.com/markets/stocks-thailand/market-movers-{category}/"
    )

    # Get request to tradingview, exit script if failed to connect.
    request: Union[str, requests.Response] = soup_ticker.request()
    if isinstance(request, str):
        print(request)
        sys.exit()

    # Fetch the site's html.
    data: bs4.ResultSet = soup_ticker.get_data(
        request=request,
        query_elements=["tr", "class", "row-EdyDtqqh listRow"],
    )

    # Clean up html and organized it into list.
    tickers: list[str] = []
    for i in range(10):
        ticker: str = str(data[i]).split("td")[0].split('"')[3].split(":")[1]
        tickers.append(ticker)

    # Fetch the respective top category's table.
    top_table_raw: list[pd.DataFrame] = pd.read_html(
        f"https://www.tradingview.com/markets/stocks-thailand/market-movers-{category}/"
    )
    top_table: pd.DataFrame = top_table_raw[0]

    return tickers, top_table


def sector_change_percentage(sector: str) -> str:

    # Exit if no sector found.
    if len(sector) <= 1:
        return "-"

    # Initiate soup class instance.
    url_sector: str = sector.replace(" ", "_")
    soup_sector_change: BEAUTIFUL_SOUP = BEAUTIFUL_SOUP(
        url=f"https://www.tradingview.com/markets/stocks-thailand/sectorandindustry-sector/{url_sector}/"
    )

    # Get request to tradingview, exit script if failed to connect.
    request: Union[str, requests.Response] = soup_sector_change.request()
    if isinstance(request, str):
        print(request)
        sys.exit()

    # Fetch the site's html.
    data: bs4.ResultSet = soup_sector_change.get_data(
        request=request,
        query_elements=[
            "div",
            "class",
            "tv-fundamental-block__value tv-fundamental-block__value--with-sign js-sector-market-change",
        ],
    )

    # Clean Data.
    percent_change = str(data[0]).split(">")[-3].split("<")[0]
    return percent_change


def create_table(data: list[tuple[list[str], pd.DataFrame]]) -> list[str]:

    sector_change_cache: dict[str, str] = {}
    table_str: list[str] = []

    for i, datum in enumerate(data):

        stock_ticker: list[str] = datum[0]
        category_table_data: pd.DataFrame = datum[1].head(10)

        # Change dataframe indexes.
        category_table_data.index = stock_ticker  # type: ignore
        category_table_data = category_table_data.drop("Ticker", axis=1).drop(
            "Employees", axis=1
        )

        # Add sector changes.
        sectors = list(category_table_data["Sector"])
        sector_percent_change: list[str] = []
        for i, sector in enumerate(sectors):
            clean_sector: str = sector.lower().replace(" ", "-")
            if clean_sector not in sector_change_cache:
                sector_change_cache[clean_sector] = sector_change_percentage(
                    clean_sector
                )
            sector_percent_change.append(sector_change_cache[clean_sector])
        category_table_data["Sector Chg % 1D"] = sector_percent_change
        table_str.append(tabulate(category_table_data, headers="keys", tablefmt="github"))  # type: ignore
    return table_str


def log_table(tables: list[str], categories: list[str]) -> None:

    for table, category in zip(tables, categories):
        logger.remove()
        logger.add(f"log/{category}.log")
        logger.log("INFO", f"\n {table}")


def edit_readme(tables: list[str]) -> None:

    readme_into: str = f"""<div align="center">

## My GitHub Statistics
<img src="https://github-readme-streak-stats.herokuapp.com/?user=nopnopwei&theme=black-ice&hide_border=true&stroke=0000&background=0D1117&ring=FFE573&fire=FF8623&currStreakLabel=FF8623" />
<img width="41%" height="195px" src="https://github-readme-stats.vercel.app/api/top-langs/?username=nopnopwei&layout=compact&hide_border=true&title_color=FEE473&text_color=FFFFFF&bg_color=0d1117" />
    
## Stocdy
<div align="left">

The tables below are data of the Thai stock market that is fetched from [TradingView](https://www.tradingview.com/markets/stocks-thailand/market-movers-all-stocks/) using [BeautifulSoup4](https://www.crummy.com/software/BeautifulSoup/bs4/doc/) and [Pandas](https://pandas.pydata.org). This README is automatically updated every day on `6:00 PM GMT+7` using [Github Actions](https://www.tradingview.com/markets/stocks-thailand/market-movers-all-stocks/). Historical data are available to view inside the `log` folder.\n"""

    readme_gainer: str = f"""### TOP GAINERS:
{tables[0]}\n"""

    readme_losers: str = f"""### TOP LOSERS:
{tables[1]}\n"""

    readme_active: str = f"""### MOST ACTIVE:
{tables[2]}\n"""

    footer: str = f"""<hr>
<div align="center">\n
README.md last auto updated on: `{date.today().strftime('%A %d %B %Y')}`
<br>
</div>
    """

    with open("README.md", "w+") as f:
        f.write(readme_into + readme_gainer + readme_losers + readme_active + footer)


if __name__ == "__main__":

    pd.options.mode.chained_assignment = None  # type: ignore

    top_gainer_data: tuple[list[str], pd.DataFrame] = get_top_data(category="gainers")
    top_losers_data: tuple[list[str], pd.DataFrame] = get_top_data(category="losers")
    top_active_data: tuple[list[str], pd.DataFrame] = get_top_data(category="active")

    clean_table: list[str] = create_table(
        data=[top_gainer_data, top_losers_data, top_active_data]
    )

    log_table(tables=clean_table, categories=["gainers", "losers", "active"])

    edit_readme(tables=clean_table)
