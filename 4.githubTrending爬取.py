import aiohttp  # 导入 aiohttp 库，用于发送异步 HTTP 请求
import asyncio  # 导入 asyncio 库，用于处理异步任务
from bs4 import BeautifulSoup  # 导入 BeautifulSoup 库，用于解析 HTML 文档
from github import Github
import os
from dotenv import load_dotenv 
load_dotenv() # 加载我们配置在.env文件中的环境变量

async def fetch_html(url):
    # 定义一个异步函数 fetch_html，用于获取 URL 对应的 HTML 内容
    async with aiohttp.ClientSession() as session:
        # 使用 aiohttp 创建一个会话上下文管理器
        async with session.get(url) as response:
            # 使用会话对象发送 GET 请求，并在响应对象上使用上下文管理器
            return await response.text()
            # 返回响应内容的文本格式

async def parse_github_trending(html):
    # 定义一个异步函数 parse_github_trending，用于解析 GitHub Trending 页面的 HTML 内容
    soup = BeautifulSoup(html, 'html.parser')
    # 使用 BeautifulSoup 解析 HTML 内容，生成一个 BeautifulSoup 对象

    repositories = []
    # 创建一个空列表，用于存储解析后的仓库信息

    g = Github(os.getenv("GITHUB_ACCESS_TOKEN"))
    # g = Github("your_access_token")
        # 使用您的 GitHub 访问令牌创建一个 Github 对象
    for article in soup.select('article.Box-row'):
        # 使用 CSS 选择器选择所有类名为 Box-row 的 article 标签
        repo_info = {}
        # 创建一个空字典，用于存储单个仓库的信息

        repo_info['name'] = article.select_one('h2 a').text.strip().replace('\n', '').replace(' ', '')
        # 获取仓库名称，使用 CSS 选择器选择 h2 标签下的 a 标签，并提取其文本内容
        print(repo_info['name'])
        repo_info['url'] = "https://github.com"+article.select_one('h2 a')['href'].strip()
        # 获取仓库 URL，使用 CSS 选择器选择 h2 标签下的 a 标签，并提取其 href 属性值,并拼接成完整的 GitHub 仓库链接

        # 获取 README.md 文件
        try:
            # 尝试获取仓库的 README.md 文件
            repo = g.get_repo(repo_info['name'])
            contents = repo.get_contents("README.md", ref="main")
            repo_info['readme'] = contents.decoded_content.decode()
            print(repo_info['readme'])
        except Exception as e:
            # 如果仓库没有 README.md 文件或发生其他错误，则打印错误信息并跳过该仓库
            print(f"Error getting README.md file for {repo_info['name'] }: {e}")
            continue
        # Description
        description_element = article.select_one('p')
        # 使用 CSS 选择器选择 p 标签
        repo_info['description'] = description_element.text.strip() if description_element else None
        # 获取仓库描述，如果存在 p 标签，则提取其文本内容，否则为 None

        # Language
        language_element = article.select_one('span[itemprop="programmingLanguage"]')
        # 使用 CSS 选择器选择 itemprop 属性为 programmingLanguage 的 span 标签
        repo_info['language'] = language_element.text.strip() if language_element else None
        # 获取仓库语言，如果存在该标签，则提取其文本内容，否则为 None

        # Stars and Forks
        stars_element = article.select('a.Link--muted')[0]
        # 使用 CSS 选择器选择类名为 Link--muted 的 a 标签，并选择第一个元素
        forks_element = article.select('a.Link--muted')[1]
        # 使用 CSS 选择器选择类名为 Link--muted 的 a 标签，并选择第二个元素
        repo_info['stars'] = stars_element.text.strip()
        # 获取仓库星标数，提取第一个元素的文本内容
        repo_info['forks'] = forks_element.text.strip()
        # 获取仓库分支数，提取第二个元素的文本内容

        # week's Stars
        today_stars_element = article.select_one('span.d-inline-block.float-sm-right')
        # 使用 CSS 选择器选择类名为 d-inline-block 和 float-sm-right 的 span 标签
        repo_info['week_stars'] = today_stars_element.text.strip() if today_stars_element else None
        # 获取本周星标数，如果存在该标签，则提取其文本内容，否则为 None

        repositories.append(repo_info)
        # 将仓库信息添加到列表中

    return repositories
    # 返回解析后的仓库信息列表


async def main():
    url = "https://github.com/trending/python?since=weekly"
    html = await fetch_html(url)
    repos = await parse_github_trending(html)

    # 格式化输出仓库信息
    format_str = "{:<5} {:<50} {:<10} {:<10} {:<10} {}"
    print(format_str.format("Rank", "Name", "Language", "Stars", "Forks", "Description"))

    for i, repo in enumerate(repos, start=1):
        print(format_str.format(i, repo["name"], repo["language"], repo["stars"], repo["forks"], repo["description"]))

if __name__ == "__main__":
    asyncio.run(main())
