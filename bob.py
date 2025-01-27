from playwright.sync_api import sync_playwright

class HTTPToolkitClient:
    def __init__(self, url="https://app.httptoolkit.tech/intercept"):
        self.url = url

    def launch_and_intercept(self):
        """Launch HTTP Toolkit and initiate Android interception using Playwright"""
        with sync_playwright() as p:
            # Launch browser in headless mode
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            try:
                # Navigate to HTTP Toolkit intercept page
                print("Navigating to HTTP Toolkit...")
                page.goto(self.url, wait_until="networkidle")

                # Wait for and click the Android ADB option
                print("Looking for Android ADB interceptor...")
                page.wait_for_selector('h1:text("Android Device via ADB")')
                page.click('h1:text("Android Device via ADB")')

                # Type the TikTok device register URL into the filter input
                print("Typing TikTok device register URL into filter...")
                page.wait_for_selector('.react-autosuggest__input')
                page.fill('.react-autosuggest__input', 'https://log16-normal-useast5.tiktokv.us/service/2/device_register/')

                # Wait for the specific request to appear
                print("Waiting for successful device register request...")
                selector = 'div[role="row"]:has-text("/service/2/device_register/"):has(div:text-is("200"))'
                page.wait_for_selector(selector)
                print("Found successful device register request!")
                
                # Click on the request row
                page.click(selector)

                # Wait for the request details to load
                print("Waiting for request details to load...")
                page.wait_for_selector('div.view-line:has-text("device_id_str")')
                page.wait_for_selector('div.view-line:has-text("new_user")')
                page.wait_for_selector('div.view-line:has-text("install_id_str")')

                # Extract values using selectors
                print("Extracting values...")
                
                def extract_value(key):
                    selector = f'div.view-line:has-text("{key}")'
                    text = page.text_content(selector)
                    import re
                    match = re.search(f'"{key}":\\s*"?(\\d+)"?', text)
                    return match.group(1) if match else None
                
                values = {
                    'device_id_str': extract_value('device_id_str'),
                    'new_user': int(extract_value('new_user')),
                    'install_id_str': extract_value('install_id_str')
                }
                
                print("\nExtracted values:")
                print(f"Device ID: {values['device_id_str']}")
                print(f"New User: {values['new_user']}")
                print(f"Install ID: {values['install_id_str']}")

                # Replace manual input with a return of the values
                return values
            finally:
                browser.close()

def main():
    client = HTTPToolkitClient()
    try:
        result = client.launch_and_intercept()
        print("\nExtracted values:")
        print(f"Device ID: {result['device_id_str']}")
        print(f"New User: {result['new_user']}")
        print(f"Install ID: {result['install_id_str']}")
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()