import requests     #爬虫
from datetime import datetime, timedelta     #时间模块
import plotly.graph_objects as go   #画图库Plotly
import os               #用于筛选并提取图片
import random           #随机背景
import streamlit as st  #网页库
import base64           #背景图片转换代码

#数据获取
def get_auto_location():
    try:
        res = requests.get("http://ip-api.com/json/?lang=zh-CN", timeout=5)
        data = res.json()
        if data.get("status") == "success":
            city = data.get("city", "").replace("市", "")
            return city
    except Exception:
        pass
    return None

#爬取
@st.cache_data(ttl=3600)             #缓存1小时内数据防封(3600秒)
def fetch_weather_data(city):        #改用API不爬取别人的网页内容
    url = "https://uapis.cn/api/v1/misc/weather"
    params = {"city": city, "forecast": "true"}  # 尝试请求预报
    headers = {"User-Agent": "Mozilla/5.0"}

    weather_list = []

    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()  # 如果状态码不是 200，直接报错跳到 except
        data = response.json()

        forecast = data.get("forecast") or data.get("daily")    #解析预报数据

        if forecast:                    #匹配URL里的数据
            today_str = datetime.now().strftime("%Y-%m-%d")     #当天日期
            tomorrow_str = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")   #明天日期
            for item in forecast[:7]:
                raw_date = item.get("date", "")[:10]    #只取"2026-11-19" 去掉时分秒
                if raw_date == today_str:                    #比对日期
                    show_week = "今天"
                elif raw_date == tomorrow_str:
                    show_week = "明天"
                else:
                    show_week = item.get("week", "")      #都不是则显示原本的星期几
                short_date = raw_date[5:] if len(raw_date) > 5 else raw_date

                weather_list.append({
                    "date": short_date,                        #日期
                    "weather": item.get("weather_day", "未知"), #天气
                    "temp": f"{item.get('temp_max', '')}°C/{item.get('temp_min', '')}°C", #温度
                    "week": show_week,                         #星期
                    "wind": item.get("wind_dir_day", ""),      #风向
                    "sunrise": item.get("sunrise", ""),        #日出
                    "sunset": item.get("sunset", ""),          #日落
                })
        else:                                 #兜底如果没预报，就把当前的实况拼成单卡片
            if data.get("temperature") is not None:
                weather_list.append({
                    "date": "今日实况",
                    "weather": data.get("weather_day", "未知"),
                    "temp": f"{data.get('temperature')}°C"
                })
                st.info("当前接口只返回了实况数据，未能获取7天预报。")

    except Exception as e:
        print(f"API请求失败：{e}")              #兜底API都挂了，返回假数据防止网页崩溃
        weather_list = [
            {"date": "接口拒绝", "weather": "未知", "temp": "--"},
            {"date": "请稍后再试", "weather": "未知", "temp": "--"}
        ]
    return weather_list

#排版区域
def display_weather_cards(data_list):   #数据
    if not data_list:
        st.warning("没有天气数据")
        return
    cols = st.columns(3)     # 创建列，横向排布，一排三个共两排

    for i, item in enumerate(data_list):
          with cols [i % 3]:
            weather_text = item['weather']
            # 匹配 Emoji 表情
            tianqitubiao = "☀️"      # 默认晴天
            if "雨" in weather_text:
                tianqitubiao = "🌧️"
            elif "多云" in weather_text:
                tianqitubiao = "☁️"
            elif "雪" in weather_text:
                tianqitubiao = "❄️"
            elif "阴" in weather_text:
                tianqitubiao = "☁️"
            elif "雷阵雨" in weather_text:
                tianqitubiao = "⛈️"
            elif "多云转晴" in weather_text:
                tianqitubiao = "⛅️"
            elif "雾" in weather_text:
                tianqitubiao = "🌫️"
            elif "龙卷风" in weather_text:
                tianqitubiao = "🌪️"
 # 2. 拼装卡片    HTML    （直接在卡片中间放一个大号 Emoji）
            card_html = f"""                   
            <div style="
                background-color: rgba(255, 255, 255, 0.85);
                border-radius: 16px;                     /* 设置卡片圆角大小，0是直角，20是超圆 */
                padding: 25px 15px;                      /* 设置内边距（卡片内部留白）*/
                text-align: center;                      /*内容居中*/
                margin: 15px;                            /* 设置外边距（卡片和卡片之间的距离） */
                box-shadow: 0 4px 10px rgba(0,0,0,0.2);
                height: 100%;                           /* 设置卡片高度 */
            ">
                 <div style="color: #333; font-size: 16px; font-weight: bold; margin-bottom: 8px;">{item['date']}</div>
                 <div style="color: #666; font-size: 18px; margin-bottom: 10px;">{item['week']}</div>
                 <div style="color: #666; font-size: 20px; margin-bottom: 15px;">{item['weather']}</div>
                 <div style="font-size: 80px; line-height: 1; margin-bottom: 15px;">{tianqitubiao}</div>
                 <div style="color: #ff4b4b; font-size: 25px; font-weight: bold; white-space: nowrap;">{item['temp']}</div>
                 <div style="color: #666; font-size: 16px; margin-bottom: 10px;">{item['wind']}</div>
                 <div style="color: #666; font-size: 15px; margin-bottom: 10px;">日出{item['sunrise'] } |  日落{item['sunset']}</div>
             </div>
            """
            st.markdown(card_html, unsafe_allow_html=True)         # 发送到网页

def display_temperature_chart(data_list):      #画曲线图
    chart_data = []

    for item in data_list:
        temp_str = item['temp']  # 提取温度比如 "20°C/15°C"
        try:
            parts = temp_str.split("/")                           #按照 "/" 切开，分成左边和右边
            high = int(parts[0].replace("°C", "").strip())        #将左边"°C" 删掉
            low = int(parts[1].replace("°C", "").strip())         #将右边"°C" 删掉
            chart_data.append({                                   #装进列表
                "日期": item['date'],
                "最高温": high,
                "最低温": low
            })
        except Exception as e:         # 如果为"今日实况" 没有斜杠的数据，跳出防止报错
            continue

    if chart_data:
      import pandas as pd
      df = pd.DataFrame(chart_data)
      fig = go.Figure()       #用 Plotly 画图
     # 最高温红线
      fig.add_trace(go.Scatter(
          x=df["日期"], y=df["最高温"],
          mode='lines+markers',    #显示线和圆点
          name='最高温',
          line=dict(color='#FF4B4B', width=3),   #用红色
          marker=dict(size=8, color='#FF4B4B', line=dict(color='white', width=2))  # 白边圆点
    ))
     # 最低温蓝线
      fig.add_trace(go.Scatter(
          x=df["日期"], y=df["最低温"],
          mode='lines+markers',
          name='最低温',
          line=dict(color='#4B9BFF', width=3),   #用蓝色
          marker=dict(size=8, color='#4B9BFF', line=dict(color='white', width=2))
    ))

      fig.update_layout(
          paper_bgcolor='rgba(0,0,0,0)',                  #外部背景透明
          plot_bgcolor='rgba(0,0,0,0)',                   #内部背景透明
          font=dict(color="#FFFFFF", weight="bold"),      #全局文字数字设为白色并且加粗
          margin=dict(l=20, r=20, t=20, b=20),            #边距变小
      legend=dict(orientation="h",yanchor="bottom",y=1.02,xanchor="right",x=1, bgcolor="rgba(0,0,0,0)",
                  font=dict(color="white"),  #将‘最高温‘’最低温’置顶并且设为白色

      ))
      fig.update_xaxes(tickfont=dict(color="white", size=12))    #X/Y 轴数字和日期加粗改白
      fig.update_yaxes(tickfont=dict(color="white", size=12))

      fig.update_xaxes(
          tickangle=-45,                       #X轴标签倾斜 45 度
          showgrid=True,gridcolor='#E5E5E5',   #灰色的网格线X轴
          zeroline=False
    )
      fig.update_yaxes(
          showgrid=True,gridcolor='#E5E5E5',   #灰色的网格线Y轴
          zeroline=False
    )

      st.plotly_chart(fig, use_container_width=True, key=f"temp_chart_{data_list[0]['date']}")   #渲染到网页，key改为第一天

def main():        #网页的标题和基础布局
    set_random_background()           #调用函数（排版）
    st.title("🌤️ 天气助手")
    auto_city = get_auto_location()   #前面的自动定位
    if auto_city:                     #网页提示框
        st.info(f"自动定位为【{auto_city}】。您可以直接点击下方按钮查询，或输入其他城市。")
    user_input = st.text_input("请输入城市/省县镇街道（如：北京市；广东省；天河区）：", value=auto_city if auto_city else "")
    if st.button("查询天气"):
        city = user_input.strip().replace("市", "").replace("区", "").replace("县", "")
        if not city:
            st.warning("没有输入城市，请重新输入。")
        else:
            st.write(f"正在查询【{city}】的天气数据...")
            data_list = fetch_weather_data(city)

            if data_list:
                st.success(f"{city}天气数据获取成功：")
                display_weather_cards(data_list[:6])   # 用卡片展示为六个为美观
                st.write("---")                    #曲线图，加个分割线
                st.markdown("<br><br><br><br><br>", unsafe_allow_html=True)    #拉开距离
                st.write("**七天气温走势**")
                st.markdown("<br><br>", unsafe_allow_html=True)          # 拉开距离
                display_temperature_chart(data_list)
                st.markdown("<br>", unsafe_allow_html=True)         # 拉开距离
            else:
                st.error("获取数据失败，可能是接口挂了，请稍后再试。")
                if not data_list:
                    st.error("获取天气失败，网页结构可能改变了。")
                else:
                    st.success(f"【{city}】未来天气获取成功：")
                    display_weather_cards(data_list)
#背景
def set_random_background():
    tuku_folder = "tuku" #背景图片来源

    if not os.path.exists(tuku_folder):
        st.error(f"找不到文件夹：{tuku_folder}，请检查！")
        return
    valid_tuku = [f for f in os.listdir(tuku_folder) if f.endswith(('.jpg', '.png', '.jpeg'))]   #拿出符合图片文件
    if not valid_tuku:
        st.warning("图库里没有找到图片文件。")
        return
    random_tuku = random.choice(valid_tuku)              #随机轮换
    bg_path = os.path.join(tuku_folder, random_tuku)     #无论Win还是Mac系统都能拼接完整的相对路径（比如 tuku/beijing.jpg）
    with open(bg_path, "rb") as f:                       #把图片转成 Base64 代码，用于网页直接读取
        encoded_string = base64.b64encode(f.read()).decode()
# CSS
    css = f"""
       <style>
       [data-testid="stAppViewContainer"] {{
           background-image: linear-gradient(rgba(0,0,0,0.4), rgba(0,0,0,0.8)), url("data:image/jpeg;base64,{encoded_string}");/*铺一层黑色渐变（越往下越黑），再铺上tuku内图片 */
           background-size: cover;                              /*图片平铺 */
           background-position: center;                         /*图片居中 */
           background-attachment: fixed;                        /*固定图片*/
       }}
    /*大标题和输入框标签变白 */
    h1, h2, h3 {{ color: white !important; }}
    [data-testid="stWidgetLabel"] p {{ color: white !important; }}
    
    /*普通段落文字变白 */
    .stMarkdown p {{ color: white !important; }}
    
    /*按钮变半透明黑底白字 */
    .stButton>button {{
        background-color: rgba(0, 0, 0, 0.6) !important;
        color: white !important;
        border: 1px solid white !important;
    }}
    }}
       }}
        </style>
       """
    st.markdown(css, unsafe_allow_html=True)

if __name__ == "__main__":              #启动方式修改
    main()

#运行      streamlit run app.py