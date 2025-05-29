import pandas as pd
from django.shortcuts import render
from django.db import connection

# 讀取資料庫內容（改用 Django 內建連線）
def load_data():
    merged = pd.read_sql_query("SELECT * FROM merged", connection)
    price = pd.read_sql_query("SELECT * FROM price", connection)
    merged['日期'] = pd.to_datetime(merged['日期'])
    price['日期'] = pd.to_datetime(price['日期'])
    return merged, price

def index(request):
    merged, price = load_data()

    brokers = ["<無>"] + sorted(merged['券商分點'].dropna().unique().tolist())
    days_options = ["1日", "5日", "20日"]

    selected_broker = request.GET.get('broker', '<無>')
    selected_days = request.GET.get('days', '1日')
    selected_stock = request.GET.get('stock')
    sort_by = request.GET.get('sort', 'count')
    reverse = request.GET.get('reverse', 'true')
    sort_reverse = reverse == 'true'

    days_col = selected_days + "報酬"

    summary = None
    table_data = []
    line_data = None

    if selected_broker != "<無>" and days_col in merged.columns:
        df = merged[merged['券商分點'] == selected_broker]
        df = df[df[days_col].notna()]
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

            # Chart.js 用資料
            if selected_stock and selected_stock in price['股票代號'].values:
                df_stock = price[price['股票代號'] == selected_stock].sort_values('日期')
                buy_dates = df[df['股票代號'] == selected_stock]['日期'].dt.strftime('%Y-%m-%d').tolist()

                line_data = {
                    "dates": df_stock['日期'].dt.strftime('%Y-%m-%d').tolist(),
                    "prices": df_stock['收盤價'].tolist(),
                    "buy_dates": buy_dates,
                    "stock_name": stock_map.get(selected_stock, ''),
                }

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
