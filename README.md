# Unnotech Backend Engineer 徵才小專案

1. [x] 抓取 http://tw-nba.udn.com/nba/index 中的焦點新聞。
2. [x] 使用 [Django](https://www.djangoproject.com/) 設計恰當的 Model，並將所抓取新聞存儲至 DB。
3. [x] 使用 [Django REST Framework](http://www.django-rest-framework.org/) 配合 AJAX 實現以下頁面：
	 * 焦點新聞列表
	 * 新聞詳情頁面
4. [x] 以 Pull-Request 的方式將代碼提交。
	
## 進階要求
1. [x] 實現爬蟲自動定時抓取。
2. [x] 使用 Websocket 服務，抓取到新的新聞時立即通知前端頁面。
3. [x] 將本 demo 部署到伺服器並可正確運行。
4. [x] 所實現新聞列表 API 可承受 100 QPS 的壓力測試。

## 專案說明
1. 部署網址：<http://15.134.87.93>
2. API 路徑：
	- 新聞列表：<http://15.134.87.93/api/news>
	- 新聞詳細內容：<http://15.134.87.93/api/news/{id}>
3. 技術組成：
	- 後端框架：Django、Django REST Framework、Django Channels
	- 資料庫：PostgreSQL
	- 快取：Redis
	- 反向代理與靜態檔案：Nginx
	- 容器化：Docker Compose（區分本機開發與正式環境）
4. 本機啟動方法：
	- 複製環境變數範本並依需求調整：
		- `cp .env.sample .env`
	- 使用本機開發環境 compose 啟動：
		- `docker compose up --build`
	- 啟動後可使用以下網址：
		- 首頁：<http://127.0.0.1:8000/>
		- 新聞列表 API：<http://127.0.0.1:8000/api/news/>
		- Django Admin：<http://127.0.0.1:8000/admin/>
	- 本機開發環境中：
		- `app` 使用 `python manage.py runserver`
		- `scrape_news` 容器會固定週期執行爬蟲
		- `db` 使用 PostgreSQL
		- `redis` 提供快取與 websocket channel layer

### 需求實作說明
1. 抓取 http://tw-nba.udn.com/nba/index 中的焦點新聞
	- 以 Django management command `scrape_news` 實作新聞爬蟲。
	- 目前依據首頁 `news_list_body` 區塊抓取新聞列表，再逐篇進入新聞詳細頁解析內容。
	- 會擷取新聞標題、作者、發佈時間、原始連結、主圖，以及內文中的文字、圖片、推文、影片等內容區塊。

2. 使用 Django 設計恰當的 Model，並將所抓取新聞存儲至 DB
	- `News` 模型負責儲存新聞主體資料。
	- `NewsTag` 模型負責儲存新聞標籤，並透過多對多關聯對應到新聞。
	- 新聞內容 `content` 以 JSON 結構儲存，保留內文區塊順序，支援：
		- 文字 `text`
		- 圖片 `image`
		- 推文 `tweet`
		- 影片 `video`
	- 資料庫正式環境使用 PostgreSQL，測試環境使用獨立設定。

3. 使用 Django REST Framework 配合 AJAX 實現頁面
	- 提供 DRF API：
		- `/api/news/`：新聞列表 API
		- `/api/news/{id}/`：新聞詳情 API
	- 前端頁面：
		- `/`：新聞列表頁
		- `/news/{id}/`：新聞詳情頁
	- 頁面載入後透過 `fetch()` 非同步呼叫 API，再以 JavaScript 將資料渲染到 HTML，因此符合 AJAX 實作要求。

4. 以 Pull-Request 的方式將代碼提交
	- 專案已依需求整理成可提交的程式碼結構，並以功能切分方式完成各項實作。

### 進階需求實作說明
1. 實現爬蟲自動定時抓取
	- `scrape_news` 支援 `--interval` 參數，可指定固定秒數循環抓取。
	- 在 Docker Compose 中另外提供 `scrape_news` service，讓爬蟲可獨立於 Web 服務持續執行。

2. 使用 Websocket 服務，抓取到新的新聞時立即通知前端頁面
	- 使用 Django Channels 與 Redis channel layer 實作 WebSocket。
	- 當爬蟲建立新新聞後，會透過 websocket group 廣播新資料。
	- 新聞列表頁會連線 `/ws/news/`，收到新文章事件後即時將卡片插入第一頁畫面。

3. 將本 demo 部署到伺服器並可正確運行
	- 已提供本機開發用 `docker-compose.yml` 與正式環境用 `docker-compose.prod.yml`。
	- 正式環境使用 `gunicorn` 啟動 Django ASGI 應用，並由 Nginx 代理請求與提供靜態檔案。
	- 服務拆分為 `app`、`scrape_news`、`db`、`redis`、`nginx`，可於伺服器上直接以 Docker Compose 啟動。

4. 所實現新聞列表 API 可承受 100 QPS 的壓力測試
	- 新聞列表 API 加入 Redis cache-aside 機制，降低重複查詢資料庫的成本。
	- 新聞詳情 API 亦加入 cache-aside 機制，降低重複讀取單篇新聞的成本。
	- API 已加入分頁，一次回傳 20 筆資料，降低單次回應負載。
	- 可使用以下指令進行壓力測試：
		- `ab -n 1000 -c 100 http://15.134.87.93/api/news/`
	- 壓力測試結果如下：
		- 新聞列表：
			- `ab -n 1000 -c 100 http://15.134.87.93/api/news/`
			- `Requests per second: 114.68 [#/sec] (mean)`
			- `Failed requests: 0`
			- 已達成需求中 API 可承受 100 QPS 的目標。
		- 新聞詳情 API：
			- `ab -n 1000 -c 100 http://15.134.87.93/api/news/1/`
			- `Requests per second: 126.31 [#/sec] (mean)`
			- `Failed requests: 0`
			- 已達成需求中 API 可承受 100 QPS 的目標。
