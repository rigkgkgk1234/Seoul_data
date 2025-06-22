from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time
import pandas as pd

def crawl_naver_cafes_by_dong(dong_name, max_count=50):
    # 1. 크롬 드라이버 설정
    options = Options()
    options.add_argument("--headless")  # 창을 띄우지 않음
    options.add_argument("--disable-gpu")  # GPU 가속 비활성화
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    # 2. 네이버 지도 접속
    driver.get("https://map.naver.com/v5")
    time.sleep(3)  # 페이지 로딩 대기

    # 3. 검색어 입력 및 실행
    try:
        search_box = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input.input_search"))
        )
        search_box.clear()
        search_box.send_keys(f"{dong_name} 카페")
        search_box.send_keys("\n")  # 엔터 키로 검색 실행
        print(f"{dong_name} 카페 검색 실행")
    except Exception as e:
        print(f"검색창 입력 실패: {e}")
        driver.quit()
        return []

    time.sleep(5)  # 검색 후 충분한 대기 시간 추가

    # 4. 장소 리스트가 들어있는 iframe 자동 탐지 (개선된 버전)
    time.sleep(5)
    iframes = driver.find_elements(By.CSS_SELECTOR, "iframe")
    found_places = False
    
    # 1단계: iframe에서 장소 리스트 찾기
    for iframe in iframes:
        driver.switch_to.default_content()
        try:
            driver.switch_to.frame(iframe)
            # 여러 CSS 선택자로 장소 리스트 찾기
            place_selectors = ["li.UEzoS", "div.kQcKJ", "div.ps-wrap", "div.ps-item"]
            for selector in place_selectors:
                places = driver.find_elements(By.CSS_SELECTOR, selector)
                if len(places) > 0:
                    found_places = True
                    print(f"iframe에서 장소 리스트를 찾았습니다. (장소 수: {len(places)})")
                    break
            if found_places:
                break
        except Exception as e:
            continue
    
    # 2단계: iframe에서 못 찾으면 메인 DOM에서 찾기
    if not found_places:
        driver.switch_to.default_content()
        place_selectors = ["li.UEzoS", "div.kQcKJ", "div.ps-wrap", "div.ps-item"]
        for selector in place_selectors:
            places = driver.find_elements(By.CSS_SELECTOR, selector)
            if len(places) > 0:
                found_places = True
                print(f"메인 DOM에서 장소 리스트를 찾았습니다. (장소 수: {len(places)})")
                break
    
    if not found_places:
        print("장소 리스트를 찾지 못했습니다. 수집을 종료합니다.")
        driver.quit()
        return []

    # 5. 장소 정보 수집
    results = []
    count = 0
    
    while count < max_count:
        # 현재 페이지의 장소 리스트 다시 가져오기
        places = driver.find_elements(By.CSS_SELECTOR, "li.UEzoS")
        if not places:
            break
            
        print(f"선택자 'li.UEzoS'로 {len(places)}개 장소 발견")
        
        for place in places:
            if count >= max_count:
                break
                
            try:
                # 이름
                try:
                    name = place.find_element(By.CSS_SELECTOR, "span.TYaxT").text
                except:
                    name = ""
                if not name:
                    continue

                # 카테고리
                try:
                    category = place.find_element(By.CSS_SELECTOR, "span.KCMnt").text
                except:
                    category = ""

                # 평점 - 리스트에서 바로 추출
                rating = ""
                try:
                    rating_spans = place.find_elements(By.CSS_SELECTOR, "span.h69bs.orXYY")
                    for span in rating_spans:
                        span_text = span.text.strip()
                        if "별점" in span_text:
                            import re
                            match = re.search(r"별점\s*([0-9]+\.[0-9]+)", span_text)
                            if match:
                                rating = match.group(1)
                                break
                except:
                    pass

                # 리뷰수 - 리스트에서 바로 추출, 999+면 상세페이지에서 재시도
                review = ""
                try:
                    h69bs_spans = place.find_elements(By.CSS_SELECTOR, "span.h69bs")
                    for s in h69bs_spans:
                        text = s.text.strip()
                        if "리뷰" in text and "별점" not in text:
                            import re
                            if "+" in text:
                                review = "999+"
                            else:
                                numbers = re.findall(r'\d+', text)
                                if numbers:
                                    review = numbers[0]
                                    break
                except:
                    pass

                # 상세페이지 클릭 (이름 링크 클릭)
                addr = ""
                try:
                    name_link = place.find_element(By.CSS_SELECTOR, "a.place_bluelink")
                    driver.execute_script("arguments[0].click();", name_link)
                    time.sleep(3)

                    driver.switch_to.default_content()
                    try:
                        detail_iframe = WebDriverWait(driver, 10).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, "iframe#entryIframe"))
                        )
                        driver.switch_to.frame(detail_iframe)

                        # 주소
                        try:
                            addr = driver.find_element(By.CSS_SELECTOR, "span.LDgIH").text
                        except:
                            addr = ""

                        # 평점 - 상세페이지에서 재시도
                        if not rating:
                            try:
                                rating_elem = driver.find_element(By.CSS_SELECTOR, "span.PXMot.LXIwF")
                                rating_text = rating_elem.text.strip()
                                import re
                                match = re.search(r"([0-9]+\.[0-9]+)", rating_text)
                                if match:
                                    rating = match.group(1)
                            except:
                                pass

                        # 리뷰수 - 999+면 상세페이지에서 재시도
                        if review == "999+" or not review:
                            try:
                                review_elem = driver.find_element(By.CSS_SELECTOR, "span.h69bs")
                                review_text = review_elem.text.strip()
                                if "방문자 리뷰" in review_text:
                                    import re
                                    numbers = re.findall(r"방문자 리뷰\s*([0-9,]+)", review_text)
                                    if numbers:
                                        review = numbers[0].replace(",", "")
                            except:
                                pass
                    except:
                        pass

                    driver.switch_to.default_content()
                    time.sleep(1)
                    try:
                        search_iframe = WebDriverWait(driver, 5).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, "iframe#searchIframe"))
                        )
                        driver.switch_to.frame(search_iframe)
                    except:
                        iframes = driver.find_elements(By.CSS_SELECTOR, "iframe")
                        for iframe in iframes:
                            try:
                                driver.switch_to.frame(iframe)
                                places = driver.find_elements(By.CSS_SELECTOR, "li.UEzoS")
                                if len(places) > 0:
                                    break
                            except:
                                driver.switch_to.default_content()
                                continue
                except Exception as e:
                    driver.switch_to.default_content()
                    time.sleep(1)
                    iframes = driver.find_elements(By.CSS_SELECTOR, "iframe")
                    for iframe in iframes:
                        try:
                            driver.switch_to.frame(iframe)
                            places = driver.find_elements(By.CSS_SELECTOR, "li.UEzoS")
                            if len(places) > 0:
                                break
                        except:
                            driver.switch_to.default_content()
                            continue

                # 빈 값은 0으로 변환
                if not rating:
                    rating = "0.0"
                if not review or review == "999+":
                    review = "0"

                # 결과 저장
                results.append({
                    "dong": dong_name,
                    "name": name,
                    "category": category,
                    "address": addr,
                    "rating": rating,
                    "review_count": review
                })
                
                count += 1
                print(f"{name} 추가됨 ({count}/{max_count}) - 평점: {rating}, 리뷰: {review}")

            except Exception as e:
                print(f"장소 정보 추출 중 오류: {e}")
                continue

        # 페이지 스크롤
        try:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
        except:
            break

    # iframe 전환 없이, 메인 DOM에서 li 태그 모두 탐색
    li_tags = driver.find_elements(By.TAG_NAME, "li")
    print(f"li 태그 개수: {len(li_tags)}")
    for idx, li in enumerate(li_tags[:10]):  # 처음 10개만 출력
        print(f"[DEBUG] li[{idx}] outerHTML:")
        print(li.get_attribute("outerHTML"))
    # 이후 실제 장소 리스트 구조에 맞는 코드로 수정 예정

    driver.quit()
    return results

# 실행
if __name__ == "__main__":
    dong = "망원동"  # 원하는 동네 입력
    results = crawl_naver_cafes_by_dong(dong, max_count=30)

    # 장소 리스트가 비어있을 때 예외 처리
    if not results:
        print("수집된 데이터가 없습니다. 결과 파일을 저장하지 않습니다.")
        exit()

    df = pd.DataFrame(results)
    
    # 리뷰수와 평점을 숫자로 변환하여 정렬
    df['review_count'] = pd.to_numeric(df['review_count'], errors='coerce')
    df['review_count'] = df['review_count'].fillna(0)
    df['rating'] = pd.to_numeric(df['rating'], errors='coerce')
    df['rating'] = df['rating'].fillna(0)
    
    # 리뷰수와 평점으로 정렬 (높은 순)
    df_sorted = df.sort_values(['review_count', 'rating'], ascending=[False, False])
    
    # 결과 저장
    df_sorted.to_csv(f"{dong}_cafe_list.csv", index=False, encoding="utf-8-sig")
    print(f"{dong}에서 {len(df_sorted)}개 카페 저장 완료")
    
    # 상위 10개 출력
    print("\n상위 10개 카페:")
    print(df_sorted[['name', 'category', 'rating', 'review_count']].head(10))