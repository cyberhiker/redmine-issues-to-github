#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4

# +--------------------------------------------------+
# | Copyright (c) AD ticket GmbH                     |
# | All rights reserved.                             |
# +--------------------------------------------------+
# | AD ticket GmbH                                   |
# | Kaiserstraße 69                                  |
# | D-60329 Frankfurt am Main                        |
# |                                                  |
# | phone: +49 (0)69 407 662 0                       |
# | fax:   +49 (0)69 407 662 50                      |
# | mail:  github@adticket.de                        |
# | web:   www.ADticket.de                           |
# +--------------------------------------------------+
# | This library is free software: you can           |
# | redistribute it and/or modify it under the terms |
# | of the GNU General Public License as published   |
# | by the Free Software Foundation, either version  |
# | 3 of the License, or (at your option) any later  |
# | version.                                         |
# |                                                  |
# | In addition you are required to retain all       |
# | author attributions provided in this software    |
# | and attribute all modifications made by you      |
# | clearly and in an appropriate way.               |
# |                                                  |
# | This software is distributed in the hope that    |
# | it will be useful, but WITHOUT ANY WARRANTY;     |
# | without even the implied warranty of             |
# | MERCHANTABILITY or FITNESS FOR A PARTICULAR      |
# | PURPOSE.  See the GNU General Public License for |
# | more details.                                    |
# |                                                  |
# | You should have received a copy of the GNU       |
# | General Public License along with this software. |
# | If not, see <http://www.gnu.org/licenses/>.      |
# +--------------------------------------------------+

'''Reads issues from a redmine API XML and adds 
them to a github repository.

@see http://www.redmine.org/projects/redmine/wiki/Rest_api
@see http://develop.github.com/

@author Markus Tacker <m@coderbyheart.de>'''

import io
import sys
from xml.dom.minidom import parse, parseString
from minidomutil import domGetText
import urllib.request
import urllib.parse
import json
from base64 import encodebytes as base64

class RedmineIssue(object):
    'Represents a redmine issue'
    def __repr__(self):
        return "redmine issue #%s: %s" % (self.id, self.subject)

class GithubIssue(object):
    'Represents a github issue'
    def __init__(self):
        self.state = 'open'
        self.labels = []
        self.milestone = None
        self.assignee = None
        
    def __repr__(self):
        return "github issue #%s: %s" % (self.id, self.title)
    
    def close(self):
        self.state = 'closed'

class RedmineIssueXML(object):
    'Represents the list of redmine redmineIssues in XML format'
    
    def __init__(self):
        pass
        
    def readXML(self, xmlfile, closedStati=None, userMap=None):
        '''Read the issues from the xml file
        closedStati: a list of redmine status ids whose tickets are closed
        userMap: a map of redmine user ids to github usernames 
        '''
        self.dom = parse(xmlfile)
        self.redmineIssues = []
        self.githubIssues = []
        self.closedStati = closedStati
        self.userMap = userMap
        for issue in self.dom.getElementsByTagName('issue'):
            self.addIssue(issue)
            
        print("Processing %d redmine issues." % len(self.redmineIssues))
        
    def addIssue(self, issueNode):
        'Creates an issue from the given node'
        issue = RedmineIssue()
        
        for key in ['project', 'tracker', 'status', 'priority', 'author', 'assigned_to', 'category', 'fixed_version', 'parent']:
            nodes = issueNode.getElementsByTagName(key)
            v = None
            if len(nodes):
                el = nodes[0]
                v = {'id': int(el.getAttribute('id')), 'name': el.getAttribute('name')}
            setattr(issue, key, v)
        
        for key in ['id', 'subject', 'description', 'start_date', 'due_date', 'done_ratio', 'estimated_hours', 'created_on', 'updated_on']:
            setattr(issue, key, domGetText(issueNode.getElementsByTagName(key)[0]))
            
        self.redmineIssues.append(issue)
        self.githubIssues.append(self.toGithubIssue(issue))
        
    def toGithubIssue(self, redmineIssue):
        'Convert a redmine issue to a github issue'
        issue = GithubIssue()
        
        if redmineIssue.status['id'] in self.closedStati:
            issue.close() 
            
        issue.id = redmineIssue.id
        issue.title = redmineIssue.subject
        issue.body = redmineIssue.description
        issue.body += "\n"
        
        for (key, label) in [('author', 'Reporter'), ('assigned_to', 'Assigned to')]:
            v = getattr(redmineIssue, key)
            if v:
                issue.body += "__%s:__ %s\n" % (label, v['name'])
        
        for (key, label) in [('start_date', 'Begin'), ('due_date', 'End'), ('done_ratio', 'Completed')]:
            v = getattr(redmineIssue, key)
            if v:
                issue.body += "__%s:__ %s\n" % (label, v)
                
        assigned_to = getattr(redmineIssue, 'assigned_to')
        if assigned_to:
            assignedId = int(assigned_to['id'])
            if assignedId in self.userMap:
                issue.assignee = self.userMap[assignedId]
        
        issue.labels.append(redmineIssue.tracker['name'])
        issue.labels.append("Prio-" + redmineIssue.priority['name'])
        if redmineIssue.category:
            issue.labels.append(redmineIssue.category['name'])
        if redmineIssue.fixed_version:
            issue.milestone = redmineIssue.fixed_version['name']
            
        return issue
            
    def publishIssues(self, user, repo, authUser, authPassword):
        '''Publish the issues to github
        
        In order to keep the redmine ticket ids we create dummy tickets
        and close the immediately.
        
        user: the github username for the repository
        repo: the github repository
        authUser: your github username
        authPassword: your github password
        '''
        
        self.baseurl = "https://api.github.com/repos/%s/%s/" % (user, repo)
        self.authData = base64(bytes(('%s:%s' % (authUser, authPassword)), 'utf-8')).decode().replace('\n', '')
       
        # Load milestone data
        # Milestones are created on demand
        self.milestones = {}
        milestonesUrl = self.baseurl + "milestones"
        for state in ['open', 'closed']:
            req = urllib.request.Request(milestonesUrl + '?state=' + state)
            req.add_header('Authorization', 'Basic %s' % self.authData)
            res = urllib.request.urlopen(req)
            for milestonedata in json.loads(res.read().decode('utf-8')):
                self.milestones[milestonedata['title']] = milestonedata
            
        # Create label data
        # Labes are created upfront
        labels = []
        for ilabels in map(lambda p: p.labels, self.githubIssues):
            for label in ilabels:
                if not label in labels:
                    labels.append(label)
        for label in labels:
            self.createLabel(label)
        self.createLabel("Dummy-Ticket")
        
        currentIssue = 1
        
        for issue in sorted(self.githubIssues, key=lambda p: int(p.id)):
            
            # Too keep the old redmine id's we have to create dummy
            # tickets
            while currentIssue < int(issue.id):
                if self.getIssue(currentIssue) == None:
                    self.createIssue("Dummy ticket %d" % currentIssue, labels=["Dummy-Ticket"])
                    self.closeIssue(currentIssue)
                currentIssue += 1
                
            # Check if milestone exists
            milestone = None
            if issue.milestone:
                if not issue.milestone in self.milestones:
                    self.createMilestone(issue.milestone)
                milestone = self.milestones[issue.milestone]['number']
                
            # Check if issue exists
            githubissuedata = self.getIssue(issue.id)
            if githubissuedata:
                print("Issue %d already exists." % int(issue.id))
                if githubissuedata['body'] != issue.body:
                    self.createComment(issue.id, issue.title + "\n\n" + issue.body)
            else:
                self.createIssue(issue.title, body=issue.body, milestone=milestone, labels=issue.labels, assignee=issue.assignee)
                # Close tickets
                if issue.state == 'closed':
                    self.closeIssue(issue.id)
    
    def getIssue(self, id):
        'Return an issue from github'
        issueUrl = self.baseurl + "issues/" + str(id)
        req = urllib.request.Request(issueUrl)
        req.add_header('Authorization', 'Basic %s' % self.authData)
        try:
            res = urllib.request.urlopen(req)
            return json.loads(res.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            else:
                raise e
            
    def createIssue(self, title, body=None, assignee=None, milestone=None, labels=None):
        'Create an issue on github'
        url = self.baseurl + "issues"
        
        issuedata = {
            'title': title,
        }
        if body:
            issuedata['body'] = body
        if assignee:
            issuedata['assignee'] = assignee
        if milestone:
            issuedata['milestone'] = milestone
        if labels:
            issuedata['labels'] = labels

        data = json.dumps(issuedata)
        clen = len(data)
        data = data.encode('utf-8')
        
        req = urllib.request.Request(url)
        req.add_header('Authorization', 'Basic %s' % self.authData)
        req.add_header('Content-Type', 'application/json')
        req.add_header('Content-Length', str(clen))
        try:
            res = urllib.request.urlopen(req, data)
            print("Created ticket %s" % title)
            return json.loads(res.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            print(e.msg)
            print(e.fp.read().decode('utf-8'))
            raise e
        
    def createComment(self, id, body):
        'Add a comment to an issue'
        url = self.baseurl + "issues/" + id + "/comments"
        
        commentdata = {
            'body': body,
        }
        data = json.dumps(commentdata)
        clen = len(data)
        data = data.encode('utf-8')
        
        req = urllib.request.Request(url)
        req.add_header('Authorization', 'Basic %s' % self.authData)
        req.add_header('Content-Type', 'application/json')
        req.add_header('Content-Length', str(clen))
        try:
            res = urllib.request.urlopen(req, data)
            print("Added comment to ticket %s" % id)
            return json.loads(res.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            print(e.msg)
            print(e.fp.read().decode('utf-8'))
            raise e
    
    def closeIssue(self, id):
        'Close an issue'
        url = self.baseurl + "issues/" + str(id)
        
        issuedata = {
            'state': 'closed',
        }
        data = json.dumps(issuedata)
        clen = len(data)
        data = data.encode('utf-8')
        
        req = MyRequest(url)
        req.method = 'PATCH'
        req.add_header('Authorization', 'Basic %s' % self.authData)
        req.add_header('Content-Type', 'application/json')
        req.add_header('Content-Length', str(clen))
        try:
            res = urllib.request.urlopen(req, data)
            print("Closed issue %d" % int(id))
            return json.loads(res.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            print(e.msg)
            print(e.fp.read().decode('utf-8'))
            raise e
    
    def getLabel(self, label):
        'Fetch a label'
        issueUrl = self.baseurl + "labels/" + label
        req = urllib.request.Request(issueUrl)
        req.add_header('Authorization', 'Basic %s' % self.authData)
        try:
            res = urllib.request.urlopen(req)
            return json.loads(res.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            else:
                raise e    
    
    def createLabel(self, label):
        'Create a label'
        if self.getLabel(label) is not None:
            return
        
        url = self.baseurl + "labels"
        
        labeldata = {
            'name': label,
        }
        data = json.dumps(labeldata)
        clen = len(data)
        data = data.encode('utf-8')
        
        req = urllib.request.Request(url)
        req.add_header('Authorization', 'Basic %s' % self.authData)
        req.add_header('Content-Type', 'application/json')
        req.add_header('Content-Length', str(clen))
        try:
            res = urllib.request.urlopen(req, data)
            print("Created label %s" % label)
            return json.loads(res.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            print(e.msg)
            print(e.fp.read().decode('utf-8'))
            raise e
    
    def createMilestone(self, title):
        'Create a milestone'
        data = json.dumps({'title':title})
        clen = len(data)
        data = data.encode('utf-8')
        url = self.baseurl + "milestones"
        
        req = urllib.request.Request(url)
        req.add_header('Authorization', 'Basic %s' % self.authData)
        req.add_header('Content-Type', 'application/json')
        req.add_header('Content-Length', str(clen))
        try:
            res = urllib.request.urlopen(req, data)
            print("Created milestone %s" % title)
            milestone = json.loads(res.read().decode('utf-8'))
            self.milestones[title] = milestone
        except urllib.error.HTTPError as e:
            print(e.msg)
            print(e.fp.read().decode('utf-8'))
            raise e
        
        
class MyRequest(urllib.request.Request):
    'This class adds custom HTTP method support'
    
    def get_method(self):
        if self.method is not None:
            return self.method
        else:
            if self.data is not None:
                return "POST"
            else:
                return "GET"

if __name__ == '__main__':   
    issuesfile = 'issues.xml'
    user = 'github-user'
    repo = 'github-repo'
    authUser = 'your-github-username'
    authPassword = 'your-github-password'
    
    rix = RedmineIssueXML()
    rix.readXML(
       issuesfile, 
       closedStati = [3,5,6], # Redmine ID of closed ticket states
       userMap = { # Map redmine user id to github usernames
           1: 'your-github-username',
           2: 'colleague-github-username',
       }
    )
    rix.publishIssues(user, repo, authUser, authPassword)
