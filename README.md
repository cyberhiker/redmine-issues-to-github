# About

## redmine_issues_to_github.py

Reads issues from a redmine API XML and adds 
them to a github repository.  This will import 
all open and closed issues from RedMine if you 
choose to download all issues from your repo.

See <http://www.redmine.org/projects/redmine/wiki/Rest_api> and  
<http://develop.github.com/>

Step 1, get Python 3.

Step 2, See this page <http://www.redmine.org/projects/redmine/wiki/Rest_api> and construct a cURL command similar to this one:

'curl -v -H "Content-Type: application/xml" -X GET -u username:password -o projectIssues.xml http://redmine/issues.xml?project_id=1&status_id=*'

Step 3, Modify the bottom of the script to be your details.


## label_manager.py

A little helper to recolor labels