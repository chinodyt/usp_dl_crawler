import requests
import json
import csv
import time

from html.parser import HTMLParser

timeout = 10

class ThesisHTMLParser(HTMLParser):
    def __init__(self, url, query = None) :
        super().__init__()
        self.fields = {}
        
        self.fields['url'] = url
        self.fields['query'] = query
        self.fields['keywords'] = []

        trying = True
        while trying :
            try :
                self.resp = requests.get(url)
                trying = False
            except :
                print(f'Failed to connect... retrying in {timeout}s...')
                time.sleep(timeout)
                timeout+=10

        self.feed(self.resp.text)
    
    def handle_starttag(self, tag, attrs):
        if tag == 'meta':
            if attrs[0] == ('name', 'DC.title') and attrs[2] == ('xml:lang', 'pt-br'):
                self.fields['title'] = attrs[1][1]
            if attrs[0] == ('name', 'DCTERMS.issued') and attrs[2] == ('xml:lang', 'pt-br'):
                self.fields['date'] = attrs[1][1]
            
            if attrs[0] == ('name', 'DC.creator') and attrs[2] == ('xml:lang', 'pt-br'):
                self.fields['author'] = attrs[1][1]
            
            if attrs[0] == ('name', 'DC.contributor') and attrs[2] == ('xml:lang', 'pt-br'):
                self.fields['advisor'] = attrs[1][1]

            if attrs[0] == ('name', 'DCTERMS.abstract') and attrs[2] == ('xml:lang', 'pt-br'):
                self.fields['abstract'] = attrs[1][1]
            if attrs[0] == ('name', 'DC.subject') and attrs[2] == ('xml:lang', 'pt-br'):
                cur_keys = [s.strip().lower() for s in attrs[1][1].split(';')]
                for k in cur_keys :
                    self.fields['keywords'].append(k)
            if attrs[0] == ('name','citation_pdf_url') :
                self.fields['pdf_url'] = attrs[1][1]
            if attrs[0] == ('name', 'citation_doi') :
                self.fields['doi'] = attrs[1][1]

    #def handle_endtag(self, tag):
    #    print("End tag  :", tag)

    #def handle_data(self, data):
    #    print("Data     :", data)

    #def handle_comment(self, data):
    #    print("Comment  :", data)

    #def handle_entityref(self, name):
    #    c = chr(name2codepoint[name])
    #    print("Named ent:", c)

    #def handle_charref(self, name):
    #    if name.startswith('x'):
    #        c = chr(int(name[1:], 16))
    #    else:
    #        c = chr(int(name))
    #    print("Num ent  :", c)

    #def handle_decl(self, data):
    #    print("Decl     :", data)
    
    @property
    def match_query(self) :
        return self.fields['query'] in self.fields['keywords']

    @property
    def return_fields(self):
        return self.fields.keys()
    

    def return_fields_as_str_list(self, list_of_fields = None, clear_newline = True) :
        ret_list = []
        if list_of_fields is None :
            list_of_fields = self.fields.keys()
        for f in list_of_fields :
            s = self.fields[f]
            if f == 'keywords' :
                s = ','.join(self.fields[f])
            if clear_newline :
                s = s.replace('\n', ' ')
            ret_list.append(s)
        return ret_list


    def __str__(self) :
        return json.dumps(self.fields, indent = 4, ensure_ascii=False).encode('utf-8').decode()



class Crawler :
    def __init__(self) :
        self.entries = []

    def query_by_keyword(self, keyword, n = 10) :
        _keyword = keyword.replace(' ', '%20')
        page = 1
        ret_list = []
        
        last_page = 10

        while len(ret_list) < n and last_page == 10:
            key_query = f"https://www.teses.usp.br/index.php?option=com_jumi&fileid=19&Itemid=87&lang=pt-br&g=1&b0={_keyword}&c0=p&o0=AND&pagina={page}"
            trying = True
            while trying :
                try :
                    resp = requests.get(key_query)
                    trying = False
                except :
                    print(f'Failed to connect... retrying in {timeout}s...')
                    time.sleep(timeout)
                    timeout+=10

            lines = resp.text.split('\n')
            last_page = 0
            for line in lines :
                if line.find('<div class="dadosDocNome"><a href=') == 0:
                    last_page += 1
                    url = line.split('"')[3]
                    cur_thesis = ThesisHTMLParser(url, keyword)
                    if cur_thesis.match_query :
                        ret_list.append(cur_thesis)
                    if len(ret_list) >= n :
                        break
            print(f"    Added {len(ret_list)}/{n}")
            page += 1
        return ret_list 

    def run(self, keyword_list, entries_per_keyword = 20) :
        for key in keyword_list :
            print(f"Trying {key}")
            cur_list = self.query_by_keyword(key, n = entries_per_keyword)
            self.entries.extend(cur_list)

    def save_as_csv(self, output, field_list, delimiter = ';', quotechar = '"', clear_newline = True) :
        with open(output, 'a') as csv_file :
            csv_writer = csv.writer(csv_file, delimiter = delimiter, quotechar = quotechar, quoting = csv.QUOTE_MINIMAL)
            for item in self.entries :
                cur_list = item.return_fields_as_str_list(field_list, clear_newline)
                csv_writer.writerow(cur_list)


