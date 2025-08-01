from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time
import pandas as pd
import re



def crawl_naver_cafes(region_name, max_count=10):
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--log-level=3')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    driver.get('https://map.naver.com/v5')
    time.sleep(5)

    # 검색창 찾기
    search_box = None
    search_selectors = [
        "input.input_search",
        "input[placeholder*='검색']",
        "input[type='text']",
        "#input_search1"
    ]

    for selector in search_selectors:
        try:
            search_box = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, selector))
            )
            break

        except:
            continue

    if not search_box:
        print("검색창을 찾지 못했습니다.")
        driver.quit()
        return []

    search_box.clear()
    search_box.send_keys(f"{region_name} 카페")
    search_box.send_keys("\n")
    print(f"[{region_name} 카페] 검색어 입력")

    time.sleep(8)

    # iframe 전환
    try:
        search_iframe = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "iframe#searchIframe")))

        driver.switch_to.frame(search_iframe)
        print("searchIframe 전환 완료")

    except:
        print("searchIframe을 찾지 못했습니다.")
        driver.quit()
        return []

    # 장소 리스트 찾기
    place_selector = [
        "li.UEzoS"
    ]

    used_selector = None
    places = []
    
    for selector in place_selector:
        try:
            places = driver.find_elements(By.CSS_SELECTOR, selector)

            if len(places) > 0:
                used_selector = selector
                # print(f"장소 리스트 셀렉터: {selector}, 개수: {len(places)}")
                print("장소 리스트 불러오기 성공")
                break

        except:
            continue

    if not places:
        print("장소 리스트를 찾지 못했습니다.")
        driver.quit()
        return []

    results = []
    count = 0
    processed_names = set()

    while count < max_count:
        places = driver.find_elements(By.CSS_SELECTOR, used_selector)

        if not places or count >= len(places):
            break

        for idx, place in enumerate(places):
            if count >= max_count:
                break

            try:
                # 항상 search_iframe으로 전환
                driver.switch_to.default_content()
                driver.switch_to.frame(search_iframe)

                # 이름 추출
                name = extract_name(place)

                if not name or name in processed_names:
                    continue

                # 카드 클릭 (상세페이지 진입)
                clicked = click_place_card(driver, place, name)

                if not clicked:
                    continue

                # 상세페이지(iframe)에서 평점/리뷰 추출
                visitor_review, blog_review = get_detail_review(driver, name)

                # entryIframe 또는 메인에서 주소 추출 (extract_address 함수 사용)
                addr = get_place_address(driver, name)

                results.append({
                    "region": region_name,
                    "name": name,
                    "address": addr,
                    "visitor_review": visitor_review,
                    "blog_review": blog_review
                })

                processed_names.add(name)
                count += 1

            except Exception as e:
                print(f"[예외] {e}")
                driver.switch_to.default_content()
                continue
        break

    driver.quit()

    return results



# 이름 추출
def extract_name(place):
    """
    여러 selector를 시도하여 장소 이름을 추출
    place: selenium element
    반환값: 이름 문자열(없으면 빈 문자열)
    """
    for sel in ["span.TYaxT", "a.place_bluelink", "span.place_name", "div.ps-title"]:
        try:
            name_elem = place.find_element(By.CSS_SELECTOR, sel)
            return name_elem.text.strip()

        except:
            continue

    return ""



# 카드 클릭
def click_place_card(driver, place, name=None):
    """
    여러 selector를 시도하여 장소 카드를 클릭
    driver: selenium webdriver
    place: selenium element
    name: (선택) 디버깅용 이름
    반환값: 클릭 성공 여부(bool)
    """
    for click_sel in ["a.place_bluelink"]:
        try:
            click_elem = place.find_element(By.CSS_SELECTOR, click_sel)
            driver.execute_script("arguments[0].scrollIntoView(true);", click_elem)

            time.sleep(0.5)
            
            driver.execute_script("arguments[0].click();", click_elem)

            if name:
                print(f"\n[{name}] 상세페이지 클릭 성공")

            time.sleep(3)

            # 항상 최상위로 전환
            driver.switch_to.default_content()
            return True

        except Exception as e:
            if name:
                print(f"[{name}] 상세페이지 클릭 실패 ({click_sel}): {e}")
            continue

    return False



# 리뷰수 추출
def extract_review_count(place):
    """
    여러 selector를 시도하여 리뷰 수를 추출
    place: selenium element
    반환값: 리뷰 수 문자열(없으면 '0')
    """
    for sel in ["span.h69bs", "span.review_count", "div.ps-review", "span[class*='review']"]:
        try:
            review_elems = place.find_elements(By.CSS_SELECTOR, sel)

            for elem in review_elems:
                text = elem.text.strip()

                if "리뷰" in text and "별점" not in text:
                    if "+" in text:
                        return "999+"

                    else:
                        nums = re.findall(r'\d+', text)

                        if nums:
                            return nums[0]

        except:
            continue

    return "0"



# '서울 OO구' 제거
def clean_address(text):
    text = re.sub(r"^서울\s*", "", text)  # 예: '서울 마포구 망원로 12' → '마포구 망원로 12'
    return text.strip()



# 주소 추출
def extract_address(driver, selectors, name=None):
    """
    주소에서 '서울 OO구' 또는 'OO구'를 제거하고 상세 주소만 추출
    """
    # 도로명 주소 우선 추출
    try:
        road_addr_divs = driver.find_elements(By.CSS_SELECTOR, "div.nQ7Lh")

        for div in road_addr_divs:
            text = div.text.strip()

            if "도로명" in text and len(text) > 10:
                cleaned = clean_address(text)

                if name:
                    print(f"[{name}] 도로명 주소 추출: {cleaned}")

                return cleaned

    except Exception as e:
        if name:
            print(f"[{name}] 도로명 주소 추출 실패: {e}")
    
    # 지번 추출 방식
    addr_elems = []

    for selector in selectors:
        try:
            addr_elems = driver.find_elements(By.CSS_SELECTOR, selector)

            if addr_elems:
                if name:
                    print(f"[{name}] 주소 태그 발견")
                break

        except:
            continue

    all_texts = [elem.text.strip() for elem in addr_elems if elem.text.strip()]
    address_keywords = ['구', '로', '길', '동', '번지', '호', '층']
    candidates = [
        clean_address(text)
        for text in all_texts
        if '상세주소 열기' not in text
        and any(kw in text for kw in address_keywords)
        and len(text) > 10
    ]

    if candidates:
        addr = max(candidates, key=len, default="")

        if name:
            print(f"[{name}] 주소 추출 성공: {addr}")

        return addr

    return ""



# 주소 추출(iframe/메인)
def get_place_address(driver, name):
    """
    entryIframe이 있으면 진입해서 주소 추출, 없으면 메인에서 주소 추출
    - driver: selenium webdriver
    - name: 장소명(디버깅용)
    반환값: 주소 문자열
    """
    addr = ""
    try:
        entry_iframe = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "iframe#entryIframe"))
        )

        print(f"[{name}] entryIframe 진입 성공")
        driver.switch_to.frame(entry_iframe)
        time.sleep(3)
        addr_selectors = [
            "span.LDgIH"
        ]
        addr = extract_address(driver, addr_selectors, name)

    except Exception as e:
        print(f"[{name}] entryIframe 진입 실패: {e}")

        try:
            time.sleep(3)
            # 주소 요소가 뜰 때까지 명시적으로 기다림
            WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "span.LDgIH"))
            )

            addr_selectors_main = [
                "div.nQ7Lh",
                "span.LDgIH"
            ]

            addr = extract_address(driver, addr_selectors_main, name)

        except Exception as e2:
            print(f"[{name}] 주소 추출 실패(메인): {e2}")

            addr = ""

    return addr



# 상세페이지(iframe)에서 리뷰 추출
def get_detail_review(driver, name=None):
    """
    entryIframe에 진입해서 방문자/블로그 리뷰 수를 각각 추출한다.
    반환값: (방문자 리뷰, 블로그 리뷰)
    """
    visitor_review = 0
    blog_review = 0

    try:
        entry_iframe = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "iframe#entryIframe"))
        )
        driver.switch_to.frame(entry_iframe)
        time.sleep(2)

        # 방문자/블로그 리뷰 분리 추출
        try:
            review_spans = driver.find_elements(By.CSS_SELECTOR, "div.dAsGb span.PXMot")

            for span in review_spans:
                text = span.text.strip().replace(',', '')

                if "방문자 리뷰" in text:
                    nums = re.findall(r'\d+', text)

                    if nums:
                        visitor_review = int(nums[0])

                elif "블로그 리뷰" in text:
                    nums = re.findall(r'\d+', text)

                    if nums:
                        blog_review = int(nums[0])

        except Exception as e:
            if name:
                print(f"[{name}] 리뷰 분리 추출 실패: {e}")

        driver.switch_to.default_content()

    except Exception as e:
        if name:
            print(f"[{name}] 상세페이지 리뷰 추출 실패: {e}")

    return visitor_review, blog_review
    


    # 기존 평점 추출 코드
    # 평점이 표시되지 않는 일이 빈번하게 일어나 삭제
    #
    # 1. get_detail_rating_review 함수 내 평점 추출
    # try:
    #     for sel in [
    #         "span.PXMot.LXIwF", "span.h69bs.orXYY", "span.rating", "div.ps-rating",
    #         "span[class*='rating']", "span.PXMot", "span[class*='PXMot']", "span[aria-label*='별점']"
    #     ]:
    #         rating_elems = driver.find_elements(By.CSS_SELECTOR, sel)
    #         for elem in rating_elems:
    #             text = elem.text.strip()
    #             m = re.search(r"([0-9]+\\.[0-9]+)", text)
    #             if m:
    #                 rating = m.group(1)
    #                 break
    #         if rating != "0.0":
    #             break
    # except Exception as e:
    #     if name:
    #         print(f"[{name}] 평점 추출 실패: {e}")
    #
    # 2. results.append에 'rating' 추가
    # "rating": rating,
    #
    # 3. DataFrame 출력/저장에 'rating' 컬럼 포함
    # print(df[['name', 'address', 'rating', 'visitor_review', 'blog_review']].to_string(index=False))



if __name__ == "__main__":
    print("\n[네이버 지도 카페 수집기]")
    print("지역 이름을 입력하면 카페를 검색, 수집합니다.")
    print("종료하려면 [exit, quit, q, 종료] 입력하세요")
    
    # 지역 이름 입력받기
    region_name = input("\n수집할 지역 이름을 입력하세요: ").strip()

    if region_name.lower() in ["exit", "quit", "q", "종료"]:
        print("프로그램을 종료합니다.")
        exit()

    if not region_name:
        print("지역을 입력해주세요.")
        exit()
    
    # 카페 수 입력받기
    max_count_input = input("수집할 카페 수를 입력하세요: ").strip()

    if not max_count_input.isdigit():
        print("숫자를 입력해주세요.")
        exit()

    max_count = int(max_count_input)

    print(f"\n[{region_name}] 카페 정보 수집 시작")

    try:
        results = crawl_naver_cafes(region_name, max_count=max_count)

        if results:
            df = pd.DataFrame(results)
            df['visitor_review'] = pd.to_numeric(df['visitor_review'], errors='coerce')
            df['visitor_review'] = df['visitor_review'].fillna(0).astype(int)
            df['blog_review'] = pd.to_numeric(df['blog_review'], errors='coerce')
            df['blog_review'] = df['blog_review'].fillna(0).astype(int)
            print(f"\n[{region_name}] 카페 리스트 (총 {len(df)}개): \n")
            print(df[['name', 'address', 'visitor_review', 'blog_review']].to_string(index=False))

            # 파일 저장: region 컬럼 제외
            save_cols = [col for col in df.columns if col != 'region']
            filename = f"{region_name}_카페리스트.csv"
            df[save_cols].to_csv(filename, index=False, encoding='utf-8-sig')
            print(f"\n파일로 저장 완료: {filename}")

        else:
            print(f"[{region_name}]에서 카페를 찾지 못했습니다.")

    except Exception as e:
        print(f"오류 발생: {e}")
    
    print("\n수집이 완료되었습니다.")