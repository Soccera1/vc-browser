import urwid
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

class Link(urwid.Button):
    def __init__(self, title, url, on_select):
        super().__init__(title)
        self.url = url
        urwid.connect_signal(self, 'click', on_select, self.url)
        self._selectable = True
        self.title = title

    def render(self, size, focus=False):
        if focus:
            text = urwid.AttrSpec('underline', 'black', 'white')
        else:
            text = urwid.AttrSpec('bold', 'black', 'light gray')
        return urwid.Button.render(self, size, focus, label=[text, self.title])

class Browser:
    def __init__(self):
        self.url_edit = urwid.Edit("URL: ", edit_text="") # Removed default URL
        self.load_button = urwid.Button("Load")
        urwid.connect_signal(self.load_button, 'click', self.load_url)
        self.header = urwid.Pile([self.url_edit, self.load_button])
        self.content_list = urwid.SimpleListWalker([])
        self.list_box = urwid.ListBox(self.content_list)
        self.main_widget = urwid.Frame(header=self.header, body=self.list_box)
        self.current_url = None

    def load_url(self, button):
        url = self.url_edit.edit_text
        self.current_url = url
        self.content_list[:] = [urwid.Text("Loading...")]
        self.loop.draw_screen() # Changed 'loop' to 'self.loop'
        try:
            response = requests.get(url)
            response.raise_for_status()
            self.parse_html(response.text, url)
        except requests.exceptions.RequestException as e:
            self.content_list[:] = [urwid.Text(f"Error: {e}")]
        except Exception as e:
            self.content_list[:] = [urwid.Text(f"An unexpected error occurred: {e}")]

    def parse_html(self, html, base_url):
        soup = BeautifulSoup(html, 'html.parser')
        content = []

        def add_element(element, is_link=False, link_url=None):
            if element:
                if is_link and link_url:
                    content.append(Link(element.strip(), link_url, self.follow_link))
                else:
                    content.append(urwid.Text(element.strip()))

        def extract_text_with_links(tag):
            parts = []
            for child in tag.contents:
                if child.name == 'a' and child.has_attr('href'):
                    href = urljoin(base_url, child['href'])
                    parts.append(('link', child.get_text()))
                elif isinstance(child, str):
                    parts.append(('text', child))
                elif child.name in ['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'div', 'span']:
                    parts.extend(extract_text_with_links(child))
                elif child.name == 'br':
                    parts.append(('text', '\n'))
            return parts

        for tag in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
            add_element(tag.get_text())
        for tag in soup.find_all('p'):
            parts = extract_text_with_links(tag)
            current_line = []
            for type, text in parts:
                if type == 'link':
                    current_line.append(Link(text, urljoin(base_url, [part[1] for part in parts if part[0] == 'link'][parts.index((type, text))]), self.follow_link))
                elif type == 'text':
                    current_line.append(urwid.Text(text))
            if current_line:
                content.append(urwid.Pile(current_line))
        for link_tag in soup.find_all('a', href=True):
            href = urljoin(base_url, link_tag['href'])
            add_element(link_tag.get_text(), is_link=True, link_url=href)

        if not content:
            content.append(urwid.Text("No content found."))
        self.content_list[:] = content

    def follow_link(self, url):
        self.url_edit.edit_text = url
        self.load_url(None) # Simulate button click

    def run(self):
        palette = [
            ('banner', 'black', 'light gray'),
            ('edit', 'light gray', 'black'),
            ('button', 'black', 'light gray'),
            ('bold', 'bold', ''),
            ('underline', 'underline', ''),
            ('focus', 'white', 'black', 'standout'),
        ]
        self.loop = urwid.MainLoop(self.main_widget, palette, unhandled_input=self.handle_input)
        self.main_widget.set_focus('header')
        self.loop.run()

    def handle_input(self, key):
        if key in ('q', 'Q'):
            raise urwid.ExitMainLoop()

if __name__ == '__main__':
    browser = Browser()
    browser.run()
