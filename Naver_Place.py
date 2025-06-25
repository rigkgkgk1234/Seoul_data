from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time
import pandas as pd

def crawl_naver_cafes_by_dong(dong_name, max_count=10):
    # 1. 크롬 드라이버 설정
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")  # GPU 가속 비활성화
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")  # 창 크기 설정
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    # 2. 네이버 지도 접속
    driver.get("https://map.naver.com/v5")
    time.sleep(5)  # 페이지 로딩 대기 시간 증가

    # 3. 검색어 입력 및 실행
    try:
        # 검색창 찾기
        search_selectors = [
            "input.input_search",
            "input[placeholder*='검색']",
            "input[type='text']",
            "#input_search1"
        ]
        
        search_box = None
        for selector in search_selectors:
            try:
                search_box = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                )
                # print(f"검색창 식별: {selector}")
                break
            except:
                continue
        
        if not search_box:
            # print("검색창 식별 불가")
            driver.quit()
            return []
            
        search_box.clear()
        search_box.send_keys(f"{dong_name} 카페")
        search_box.send_keys("\n")  # 엔터 키로 검색 실행
        print(f"{dong_name} 카페 검색")
    except Exception as e:
        print(f"검색창 입력 실패: {e}")
        driver.quit()
        return []

    time.sleep(8)  # 검색 후 대기 시간

    # 4. iframe 탐지 및 전환
    # print("iframe 탐지 시작")
    iframes = driver.find_elements(By.CSS_SELECTOR, "iframe")
    # print(f"발견된 iframe 개수: {len(iframes)}")
    
    for i, iframe in enumerate(iframes):
        try:
            iframe_id = iframe.get_attribute("id")
            iframe_src = iframe.get_attribute("src")
            # print(f"iframe[{i}]: id={iframe_id}, src={iframe_src}")
        except:
            print(f"iframe[{i}]: 정보 추출 실패")
    
    # searchIframe 찾기
    search_iframe = None
    try:
        search_iframe = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "iframe#searchIframe"))
        )
        print("searchIframe 발견")
    except:
        print("searchIframe 발견 실패 다른 iframe 시도")
        # searchIframe이 없으면 첫 번째 iframe 시도
        if iframes:
            search_iframe = iframes[0]
            print("첫 번째 iframe 사용")
    
    if not search_iframe:
        print("사용할 수 있는 iframe이 없음")
        driver.quit()
        return []
    
    # searchIframe으로 전환
    try:
        driver.switch_to.frame(search_iframe)
        print("iframe 전환 완료")
    except Exception as e:
        print(f"iframe 전환 실패: {e}")
        driver.quit()
        return []

    # 5. 장소 리스트 찾기
    time.sleep(3)
    
    # 여러 CSS 선택자로 장소 리스트 찾기
    place_selectors = [
        "li.UEzoS",
        "div.kQcKJ", 
        "div.ps-wrap",
        "div.ps-item",
        "li[data-laim-item-id]",
        "div.ps-wrap > div",
        "div[data-laim-item-id]"
    ]
    
    places = []
    used_selector = None
    
    for selector in place_selectors:
        try:
            places = driver.find_elements(By.CSS_SELECTOR, selector)
            if len(places) > 0:
                used_selector = selector
                print(f"장소 리스트 발견: {selector} (개수: {len(places)})")
                break
        except Exception as e:
            print(f"선택자 {selector} 실패: {e}")
            continue
    
    if not places:
        print("장소 리스트 발견 실패")
        # 현재 페이지의 HTML 구조 확인
        try:
            page_source = driver.page_source
            # print("현재 페이지 HTML 구조:")
            # print(page_source[:2000])  # 처음 2000자만 출력
        except:
            print("HTML 구조 확인 실패")
        driver.quit()
        return []

    # 6. 장소 정보 수집
    max_pages = 3
    results = []
    count = 0
    processed_names = set()  # 중복 방지를 위한 set
    page_num = 1
    
    while count < max_count and page_num <= max_pages:
        # 현재 페이지의 장소 리스트 다시 가져오기
        places = driver.find_elements(By.CSS_SELECTOR, used_selector)
        if not places:
            print("더 이상 장소가 없음")
            break
        print(f"현재 페이지({page_num})에서 {len(places)}개 장소 발견")
        
        for place in places:
            if count >= max_count:
                break
            try:
                # 이름 추출 (여러 선택자 시도)
                name = ""
                name_selectors = ["span.TYaxT", "a.place_bluelink", "span.place_name", "div.ps-title"]
                for selector in name_selectors:
                    try:
                        name_elem = place.find_element(By.CSS_SELECTOR, selector)
                        name = name_elem.text.strip()
                        if name:
                            break
                    except:
                        continue
                if not name:
                    print("이름 찾을 수 없음")
                    continue
                # 중복 체크
                if name in processed_names:
                    print(f"중복된 장소 건너뛰기: {name}")
                    continue
                # 카테고리 추출
                category = ""
                category_selectors = ["span.KCMnt", "span.category", "div.ps-category"]
                for selector in category_selectors:
                    try:
                        category_elem = place.find_element(By.CSS_SELECTOR, selector)
                        category = category_elem.text.strip()
                        if category:
                            break
                    except:
                        continue
                # 평점 추출 (리스트에서)
                rating = "0.0"  # 기본값을 0.0으로 설정
                rating_selectors = ["span.h69bs.orXYY", "span.rating", "div.ps-rating", "span[class*='rating']"]
                for selector in rating_selectors:
                    try:
                        rating_elems = place.find_elements(By.CSS_SELECTOR, selector)
                        for elem in rating_elems:
                            text = elem.text.strip()
                            if "별점" in text or "." in text:
                                import re
                                match = re.search(r"([0-9]+\.[0-9]+)", text)
                                if match:
                                    rating = match.group(1)
                                    break
                        if rating != "0.0":
                            break
                    except:
                        continue
                
                # 리뷰수 추출 (리스트에서)
                review = "0"
                review_selectors = ["span.h69bs", "span.review_count", "div.ps-review", "span[class*='review']"]
                for selector in review_selectors:
                    try:
                        review_elems = place.find_elements(By.CSS_SELECTOR, selector)
                        for elem in review_elems:
                            text = elem.text.strip()
                            if "리뷰" in text and "별점" not in text:
                                import re
                                if "+" in text:
                                    review = "999+"
                                else:
                                    numbers = re.findall(r'\d+', text)
                                    if numbers:
                                        review = numbers[0]
                                        break
                        if review != "0":
                            break
                    except:
                        continue
                
                # 평점이 0.0이어도 리뷰수가 있으면 포함
                if review == "0":
                    continue
                
                addr = ""
                results.append({
                    "dong": dong_name,
                    "name": name,
                    "category": category,
                    "address": addr,
                    "rating": rating,
                    "review_count": review
                })
                processed_names.add(name)
                count += 1
                print(f"{name} 추가됨 ({count}/{max_count}) - 평점: {rating}, 리뷰: {review}")
            except Exception as e:
                print(f"장소 정보 추출 중 오류: {e}")
                continue
        
        # 다음 페이지 버튼 클릭
        if page_num >= max_pages:
            print(f"최대 페이지({max_pages})에 도달하여 종료")
            break
        
        # 충분히 스크롤하여 새로운 카페들을 로딩
        print("스크롤 중..")
        scroll_count = 0
        max_scrolls = 10  # 최대 스크롤 횟수
        
        while scroll_count < max_scrolls:
            # 현재 장소 개수 확인
            current_places = len(driver.find_elements(By.CSS_SELECTOR, used_selector))
            
            # 페이지 끝까지 스크롤
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            
            # 새로운 장소 개수 확인
            new_places = len(driver.find_elements(By.CSS_SELECTOR, used_selector))
            
            print(f"스크롤 {scroll_count + 1}: {current_places}개 → {new_places}개 장소")
            
            # 새로운 장소가 로딩되지 않으면 스크롤 중단
            if new_places <= current_places:
                scroll_count += 1
                if scroll_count >= 3:  # 3번 연속으로 새 장소가 없으면 중단
                    break
            else:
                scroll_count = 0  # 새로운 장소가 로딩되면 카운터 리셋
            
            scroll_count += 1
        
        print("다음 페이지 버튼을 찾는 중..")
        
        try:
            # svg.yUtES 선택자로 다음 페이지 버튼 찾기
            next_selectors = [
                'svg.yUtES',
                'a svg.yUtES',
                'button svg.yUtES',
                'a[aria-label*="다음"]',
                'button[aria-label*="다음"]',
                'a[title*="다음"]',
                'button[title*="다음"]'
            ]
            
            next_btn = None
            for selector in next_selectors:
                try:
                    next_btn = driver.find_element(By.CSS_SELECTOR, selector)
                    if next_btn:
                        # svg 요소인 경우 부모 요소(클릭 가능한 요소) 찾기
                        if 'svg' in selector:
                            next_btn = next_btn.find_element(By.XPATH, "./..")
                        print(f"다음 페이지 발견: {selector}")
                        break
                except:
                    continue
            
            if next_btn and next_btn.is_enabled():
                driver.execute_script("arguments[0].click();", next_btn)
                time.sleep(3)
                page_num += 1
                
                # 페이지 전환 후 iframe 재전환
                driver.switch_to.default_content()
                time.sleep(1)
                try:
                    search_iframe = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "iframe#searchIframe"))
                    )
                    driver.switch_to.frame(search_iframe)
                    print("새 페이지의 iframe으로 전환 완료")
                except:
                    print("새 페이지의 iframe 전환 실패")
                    break
            else:
                print("다음 페이지 버튼을 찾을 수 없거나 비활성화 상태")
                break
        except Exception as e:
            print(f"다음 페이지 버튼 클릭 실패: {e}")
            break
    driver.quit()
    return results

# 리뷰수 정렬
def review_sort_key(x):
    if x == '999+':
        return 1e9
    try:
        return int(x)
    except:
        return 0


if __name__ == "__main__":
    # 서울 동 리스트 불러오기
    seoul_code = pd.read_csv('data/Seoul_code.csv')
    # '읍면동명' 컬럼에서 결측치 제거 및 중복 제거
    dong_list = seoul_code['읍면동명'].dropna().unique().tolist()
    print(f"서울 동 개수: {len(dong_list)}")

    all_results = []
    for idx, dong in enumerate(dong_list):
        print(f"\n[{idx+1}/{len(dong_list)}] {dong} 카페 수집 시작..")
        try:
            results = crawl_naver_cafes_by_dong(dong, max_count=10)
            if results:
                all_results.extend(results)
                print(f"{dong} 카페 {len(results)}개 수집 완료")
            else:
                print(f"{dong}에서 카페를 찾지 못함")
        except Exception as e:
            print(f"{dong} 수집 중 오류: {e}")
            continue
    # 데이터프레임 변환 및 저장
    df = pd.DataFrame(all_results)
    if not df.empty:
        df['review_count_sort'] = df['review_count'].apply(review_sort_key)
        df['rating'] = pd.to_numeric(df['rating'], errors='coerce')
        df['rating'] = df['rating'].fillna(0)
        df_sorted = df.sort_values(['review_count_sort', 'rating'], ascending=[False, False])
        df_sorted.to_csv('seoul_all_cafe_list.csv', index=False, encoding='utf-8-sig')
        print(f"\n서울 전체 {len(df_sorted)}개 카페 저장 완료 (seoul_all_cafe_list.csv)")
        print("\n상위 10개 카페:")
        print(df_sorted[['dong', 'name', 'category', 'rating', 'review_count']].head(10))
    else:
        print("수집된 데이터가 없음") 