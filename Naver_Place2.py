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


def crawl_naver_cafes_by_dong(dong_name, max_count=10):
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
    search_box.send_keys(f"{dong_name} 카페")
    search_box.send_keys("\n")
    print(f"'{dong_name} 카페' 검색어 입력 완료")
    time.sleep(8)

    # iframe 전환
    try:
        search_iframe = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "iframe#searchIframe"))
        )
        driver.switch_to.frame(search_iframe)
        print("searchIframe 전환 완료")
    except:
        print("searchIframe을 찾지 못했습니다.")
        driver.quit()
        return []

    # 장소 리스트 찾기
    place_selectors = [
        "li.UEzoS",
        "li.VLTHu",
        "div.place-list-item",
        "li[data-laim-item-id]",
        "div[data-laim-item-id]"
    ]
    used_selector = None
    places = []
    for selector in place_selectors:
        try:
            places = driver.find_elements(By.CSS_SELECTOR, selector)
            if len(places) > 0:
                used_selector = selector
                print(f"장소 리스트 셀렉터: {selector}, 개수: {len(places)}")
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
                rating, visitor_review, blog_review = get_detail_rating_review(driver, name)
                # entryIframe 또는 메인에서 주소 추출 (extract_address 함수 사용)
                addr = get_place_address(driver, name)
                results.append({
                    "dong": dong_name,
                    "name": name,
                    "address": addr,
                    "rating": rating,
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
    여러 selector를 시도하여 장소 이름을 추출하는 함수.
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
    여러 selector를 시도하여 장소 카드를 클릭하는 함수.
    driver: selenium webdriver
    place: selenium element
    name: (선택) 디버깅용 이름
    반환값: 클릭 성공 여부(bool)
    """
    for click_sel in [".header_text_area", ".btn_place_card", "a.place_bluelink"]:
        try:
            click_elem = place.find_element(By.CSS_SELECTOR, click_sel)
            driver.execute_script("arguments[0].scrollIntoView(true);", click_elem)
            time.sleep(0.5)
            driver.execute_script("arguments[0].click();", click_elem)
            if name:
                print(f"[{name}] 상세페이지 클릭 성공 ({click_sel})")
            time.sleep(3)
            # 항상 최상위로 전환
            driver.switch_to.default_content()
            return True
        except Exception as e:
            if name:
                print(f"[{name}] 상세페이지 클릭 실패 ({click_sel}): {e}")
            continue
    return False


# 평점 추출
def extract_rating(place):
    """
    여러 selector를 시도하여 평점을 추출하는 함수.
    place: selenium element
    반환값: 평점 문자열(없으면 '0.0')
    """
    for sel in ["span.h69bs.orXYY", "span.rating", "div.ps-rating", "span[class*='rating']"]:
        try:
            rating_elems = place.find_elements(By.CSS_SELECTOR, sel)
            for elem in rating_elems:
                text = elem.text.strip()
                m = re.search(r"([0-9]+\.[0-9]+)", text)
                if m:
                    return m.group(1)
        except:
            continue
    return "0.0"


# 리뷰수 추출
def extract_review_count(place):
    """
    여러 selector를 시도하여 리뷰 수를 추출하는 함수.
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


# 주소 추출
def extract_address(driver, selectors, name=None):
    """
    여러 CSS selector를 받아 주소 후보를 찾고, 도로명 주소가 있으면 우선 반환,
    없으면 기존 방식(지번 등)으로 가장 긴 텍스트 반환.
    """
    # 1. 도로명 주소 우선 추출
    try:
        road_addr_divs = driver.find_elements(By.CSS_SELECTOR, "div.nQ7Lh")
        for div in road_addr_divs:
            text = div.text.strip()
            if "도로명" in text and len(text) > 10:
                if name:
                    print(f"[{name}] 도로명 주소 추출: {text}")
                return text
    except Exception as e:
        if name:
            print(f"[{name}] 도로명 주소 추출 실패: {e}")
    # 2. 기존 방식 (지번 등)
    addr_elems = []
    for selector in selectors:
        try:
            addr_elems = driver.find_elements(By.CSS_SELECTOR, selector)
            if addr_elems:
                if name:
                    print(f"[{name}] 주소 선택자 성공: {selector}")
                break
        except:
            continue
    all_texts = [elem.text.strip() for elem in addr_elems if elem.text.strip()]
    print(f"[{name}] 주소 후보 텍스트: {all_texts}")
    address_keywords = ['구', '로', '길', '동', '번지', '호', '층']
    candidates = [
        text for text in all_texts
        if '상세주소 열기' not in text
        and any(kw in text for kw in address_keywords)
        and len(text) > 10
    ]
    if candidates:
        addr = max(candidates, key=len, default="")
        if name:
            print(f"[{name}] 주소 최종 선택: {addr}")
        return addr


# 주소 추출(iframe/메인)
def get_place_address(driver, name):
    """
    entryIframe이 있으면 진입해서 주소 추출, 없으면 메인에서 주소 추출.
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
            "div.nQ7Lh",
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


# 상세페이지(iframe)에서 평점/리뷰 추출

def get_detail_rating_review(driver, name=None):
    """
    entryIframe에 진입해서 평점과 방문자/블로그 리뷰 수를 각각 추출한다.
    반환값: (평점, 방문자 리뷰, 블로그 리뷰)
    """
    rating = "0.0"
    visitor_review = 0
    blog_review = 0
    try:
        entry_iframe = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "iframe#entryIframe"))
        )
        driver.switch_to.frame(entry_iframe)
        time.sleep(2)
        # 평점 추출
        for sel in ["span.PXMot.LXIwF", "span.h69bs.orXYY", "span.rating", "div.ps-rating", "span[class*='rating']"]:
            try:
                rating_elems = driver.find_elements(By.CSS_SELECTOR, sel)
                for elem in rating_elems:
                    text = elem.text.strip()
                    m = re.search(r"([0-9]+\.[0-9]+)", text)
                    if m:
                        rating = m.group(1)
                        break
                if rating != "0.0":
                    break
            except:
                continue
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
            print(f"[{name}] 상세페이지 평점/리뷰 추출 실패: {e}")
    return rating, visitor_review, blog_review



if __name__ == "__main__":
    print("\n[네이버 지도 카페 수집기]")
    print("동 이름을 입력하면 카페를 검색, 수집합니다.")
    print("종료하려면 [exit, quit, q, 종료] 입력하세요")
    
    # 동 이름 입력받기
    dong_name = input("\n수집할 지역 이름을 입력하세요(동 단위): ").strip()

    if dong_name.lower() in ["exit", "quit", "q", "종료"]:
        print("프로그램을 종료합니다.")
        exit()

    if not dong_name:
        print("동 단위로 입력해주세요.")
        exit()
    
    # 카페 수 입력받기
    max_count_input = input("수집할 카페 수를 입력하세요: ").strip()
    if not max_count_input.isdigit():
        print("숫자를 입력해주세요.")
        exit()
    max_count = int(max_count_input)

    print(f"\n[{dong_name}] 카페 정보 수집 중...")
    try:
        results = crawl_naver_cafes_by_dong(dong_name, max_count=max_count)
        if results:
            df = pd.DataFrame(results)
            df['visitor_review'] = pd.to_numeric(df['visitor_review'], errors='coerce')
            df['visitor_review'] = df['visitor_review'].fillna(0).astype(int)
            df['blog_review'] = pd.to_numeric(df['blog_review'], errors='coerce')
            df['blog_review'] = df['blog_review'].fillna(0).astype(int)
            print(f"\n[{dong_name}] 카페 리스트 (총 {len(df)}개):")
            print(df[['name', 'address', 'rating', 'visitor_review', 'blog_review']].to_string(index=False))
            # 파일 저장: dong 컬럼 제외
            save_cols = [col for col in df.columns if col != 'dong']
            filename = f"{dong_name}_카페리스트.csv"
            df[save_cols].to_csv(filename, index=False, encoding='utf-8-sig')
            print(f"\n파일로 저장 완료: {filename}")
        else:
            print(f"[{dong_name}]에서 카페를 찾지 못했습니다.")
    except Exception as e:
        print(f"오류 발생: {e}")
    
    print("\n수집이 완료되었습니다.")