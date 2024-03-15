#! /usr/bin/python3

import markdown
from markdown.treeprocessors import etree
import re
import datetime

#read RSS feed file and make a list of existing entry titles
rss_file = "rss" 
rss_out_tree = etree.parse(rss_file) 
rss_out_root = rss_out_tree.getroot()
existing_item_title_elements = rss_out_tree.findall(".//item/title") #get all existing item titles
existing_item_titles = list()
for existing_item_title_element in existing_item_title_elements:
    existing_item_titles.append(existing_item_title_element.text)

#read the markdown source file
with open("docs/README.md", "r") as md_file: #this filename may need to be updated once we know where the product changelog will be published
    md_text = md_file.read()

#get a all entry in the markdown file, store them in a list, and reverse the list so the entries are processed from oldest to newest   
entries = re.findall("\*\*\*\n\n(## [\n \S]*?(?=\n\*\*\*|\Z))",md_text)
entries.reverse() 

def process_new_entry():
    item_out = "<item></item>"
    item_out_tree = etree.fromstring(item_out)
    item_title = etree.Element("title")
    item_out_tree.insert(0,item_title)
    item_title.text = entry_title_text
    item_pubDate = etree.Element("pubDate")
    item_out_tree.insert(1, item_pubDate)
    item_pubDate.text = str(f"{item_timestamp}") #update the timestamp for the item
    item_link = etree.Element("link")
    item_out_tree.insert(2, item_link)
    item_link.text = entry_URL
    item_guid = etree.Element("guid")
    item_out_tree.insert(3, item_guid)
    item_guid.text = f"{entry_URL}_{item_month}_{item_day}_{item_year}"
    item_description = etree.Element("description")
    item_out_tree.insert(4, item_description)
    item_description.text = f"{entry_body_text_html}"
    rss_out_root[0].insert(6,item_out_tree) # insert(6 <-- update this number if any more elements are added before the first <item>... it would be nice if we could find the right number rather than hard-coding it

for entry in entries: 
    entry_text = re.search("^## ([\S ]*?)\n\n([\S ]*?)\n\n(\*\*([\S ]*?)\*\*\n\n|)([\S\s]*?)\Z",entry)
    entry_title_text = entry_text.group(1)
    entry_title_for_url = str(entry_title_text).replace("—","").replace(" - "," ").replace("’","").replace('"','').replace(":","") 
    entry_date_text = entry_text.group(2)
    item_date = re.search("^([A-Za-z]*?) (\d{1,2}), (\d{4})",entry_date_text)
    item_month = item_date.group(1)
    item_day = item_date.group(2)
    item_year = item_date.group(3)
    item_datetime_string = f"{item_month} {item_day} {item_year}" #make string from month day and year of entry
    item_datetime_object = datetime.datetime.strptime(item_datetime_string, "%B %d %Y") # convert string to datetime object
    item_timestamp = item_datetime_object.strftime("%a, %d %b %Y %H:%M:%S GMT") # make timestamp string from datetime object. cheated for PoC by adding GMT so that this looks like a valid RFC-822 date-time https://validator.w3.org/feed/docs/error/InvalidRFC2822Date.html   
    entry_category = entry_text.group(4)
    entry_body_text = entry_text.group(5)
    entry_body_text = entry_body_text.replace(".gitbook/assets/","https://github.com/snyk/product-updates-docs/gitbook/assets/") #make path to images absolute rather than relative
    entry_body_text_html = markdown.markdown(entry_body_text)
    if entry_category != "":
        entry_body_text_html = f"<p><b>{entry_category}</b></p>{entry_body_text_html}"
    entry_URL = f"https://snyk.gitbook.io/product-updates#{str(entry_title_for_url).replace(' ', '-')}" #this URL will need to be updated once we know where the product changelog will be published
    if entry_title_text in existing_item_titles: #if entry title is in the output file, check if the <item> <pubDate> matches item_timestamp
        item_pubDates = list()
        for item_pubDate in rss_out_root.findall(str(f"./channel/item[title='{entry_title_text}']/pubDate")): 
            item_pubDates.append(item_pubDate.text)
        if item_timestamp in item_pubDates: #if the <item> <pubDate> matches item_timestamp check to see if the item description matches the entry body text HTML
            for item_description in rss_out_root.findall(str(f"./channel/item[title='{entry_title_text}'][pubDate='{item_timestamp}']/description")): 
                if item_description.text == entry_body_text_html: # if the item description matches the entry body text HTML, do nothing
                    pass
                else:
                    item_description.text = entry_body_text_html # if the item description doesn't match the entry body HTML, update the description to match.
        else: #if entry title is in the output file and the <item> <pubDate> does not match item_timestamp, treat it as a new entry
            process_new_entry() 
    else: #if the entry is not in the output file, add it as the first <item> in <channel> after <pubDate>. 
        process_new_entry()
for channel_pubDate in rss_out_root.findall("./channel/pubDate"): #update the timestamp for the feed
    channel_timestamp = datetime.datetime.now().strftime(f"%a, %d %b %Y %H:%M:%S GMT") #cheated for PoC by adding GMT so that this looks like a valid RFC-822 date-time https://validator.w3.org/feed/docs/error/InvalidRFC2822Date.html
    channel_pubDate.text = str(channel_timestamp)
etree.indent(rss_out_tree, space="\t") #this is what makes the output pretty
rss_out_tree.write(rss_file) 
