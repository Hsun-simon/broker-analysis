import pandas as pd
from django.shortcuts import render
from sqlalchemy import create_engine
from django.conf import settings

# 根據 dj_database_url 設定動態建立 SQLAlchemy engine（for PostgreSQL）
db_conf = settings.DATABASES['default']
DB_URL = f"postgresql://{db_conf['USER']}:{db_conf['PASSWORD']}@{db_conf['HOST']}:{db_conf['PORT']}/{db_conf['NAME']}"
engine = create_engine(DB_URL)

def load_data(selected_broker=None, selected_stock=None):
    merged_query = "SELECT * FROM merged"
    price_query = "SELECT * FROM price"

    if selected_broker:
        merged_query += f" WHERE \"券商分點\" = '{selected_broker}'"

    if selected_stock:
        price_query += f" WHERE \"股票代號\" = '{selected_stock}'"

    merged = pd.read_sql_query(merged_query, engine) if selected_broker else pd.DataFrame()
    price = pd.read_sql_query(price_query, engine) if selected_stock else pd.DataFrame()

    if not merged.empty:
        merged['日期'] = pd.to_datetime(merged['日期'])
    if not price.empty:
        price['日期'] = pd.to_datetime(price['日期'])

    return merged, price

def index(request):
    selected_broker = request.GET.get('broker', '<無>')
    selected_stock = request.GET.get('stock')
    selected_days = request.GET.get('days', '1日')
    sort_by = request.GET.get('sort', 'count')
    reverse = request.GET.get('reverse', 'true')
    sort_reverse = reverse == 'true'
    days_col = selected_days + "報酬"

    summary = None
    table_data = []
    line_data = None
    merged = pd.DataFrame()
    price = pd.DataFrame()

    if selected_broker != "<無>":
        merged, _ = load_data(selected_broker=selected_broker)

        if days_col in merged.columns:
            df = merged[merged[days_col].notna()]
            if not df.empty:
                avg = df[days_col].mean()
                win_rate = (df[days_col] > 0).mean()
                summary = f"平均報酬率：{avg*100:.2f}%｜勝率：{win_rate*100:.2f}%｜樣本數：{len(df)}"

                df_group = (
                    df.groupby('股票代號')[days_col]
                    .agg(['mean', 'count'])
                    .sort_values(by=sort_by, ascending=not sort_reverse)
                    .head(10)
                )

                stock_map = (
                    merged[['股票代號', '名稱']]
                    .drop_duplicates()
                    .set_index('股票代號')['名稱']
                    .to_dict()
                )

                table_data = [
                    {
                        "id": idx,
                        "name": f"{stock_map.get(idx, '')}（{idx}）",
                        "mean": f"{row['mean'] * 100:.2f}",
                        "count": int(row['count']),
                    }
                    for idx, row in df_group.iterrows()
                ]

                if selected_stock:
                    _, price = load_data(selected_stock=selected_stock)
                    df_stock = price.sort_values('日期')
                    buy_dates = df[df['股票代號'] == selected_stock]['日期'].dt.strftime('%Y-%m-%d').tolist()

                    line_data = {
                        "dates": df_stock['日期'].dt.strftime('%Y-%m-%d').tolist(),
                        "prices": df_stock['收盤價'].tolist(),
                        "buy_dates": buy_dates,
                        "stock_name": stock_map.get(selected_stock, ''),
                    }

    all_brokers = pd.read_sql_query("SELECT DISTINCT \"券商分點\" FROM merged", engine)
    brokers = ["<無>"] + sorted(all_brokers['券商分點'].dropna().tolist())
    days_options = ["1日", "5日", "20日"]

    return render(request, 'analysis/index.html', {
        "brokers": brokers,
        "days_options": days_options,
        "selected_broker": selected_broker,
        "selected_days": selected_days,
        "summary": summary,
        "table_data": table_data,
        "line_data": line_data,
        "sort_by": sort_by,
        "sort_reverse": sort_reverse,
    })
