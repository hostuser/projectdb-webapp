# This file will generate a docx summary of the projects in projectsdb
# Warning: This script will dump images into the folder it's run from
# Python docx requires the lxml and PIL modules, see https://github.com/mikemaccana/python-docx and
# http://www.lfd.uci.edu/~gohlke/pythonlibs/#lxml
# http://www.lfd.uci.edu/~gohlke/pythonlibs/#pillow
# Replace \pythondocx\template\word\styles.xml with your desired style template
# Pythondocx has been modified to support header row style changes
# By Martin Feller, Nick Young

import sys
import shlex
import subprocess
import _mysql
from datetime import datetime
import pprint
import generate_research_outcomes_and_scalings_docx_example_config
from pythondocx.docx import *
import urllib2

# @IndentOk

# Don't print output if on blacklist
blacklist = {
  'institutions': ['University of Western Australia', 'University of Adelaide', 'New York University', 'Argonne National Lab', 'University of Sydney'],
  'departments1': [],
  'departments2': []
}

# Print only output if on whitelist
whitelist = {
  'institutions': [],
  'departments1': [],
  'departments2': []
}

# Don't underline institutions and departments
skip_formatting = 1

if not os.path.exists('img') : os.mkdir('img')

def query(sqlQuery):
  ''' Run a SQL query against the project database '''
  global db
  db.query(sqlQuery)
  r = db.store_result()
  result = r.fetch_row(maxrows=0, how=1)
  return result

def removeNonAscii(s):
  ''' Remove non-ascii and defined html tags from string '''
  filtered = "".join(c for c in s if ord(c)<127 and ord(c)>31)
  # replace br with newline
  filtered = filtered.replace('<br/>','\n')
  filtered = filtered.replace('<br>','\n')
  filtered = filtered.replace('<li>','\n')
  # remove other html
  filtered = re.sub('<[^<]+?>', '', filtered)
  return filtered

def downloadAndSaveImage(url, path):
  ''' Download and save an image. Set user agent header to avoid
      errors from web pages checking for recognised user agents.
      Returns true on success, false on failure
  '''
  try :
    req = urllib2.Request(url, headers={'User-Agent' : "Mozilla/5.0"})
    img = urllib2.urlopen(req)
    if img.headers.maintype == 'image':
      buf = img.read()
      downloaded_image = file(path, "wb")
      downloaded_image.write(buf)
      downloaded_image.close()
      img.close()
      return True
    else:
      raise Exception("%s is not an image!" % url)
      return False
  except urllib2.HTTPError, err:
    if err.code == 404:
       print "%s 404'd!" % url
    elif err.code == 403:
       print "%s is 403!" % url
    else:
       print "%s when fetching %s" % err.code, url
    return False

def scaleImage(path):
  ''' Scale image. docx apparently can't do it '''
  global pic_width
  img = Image.open(path)
  wpercent = (pic_width/float(img.size[0]))
  hsize = int((float(img.size[1])*float(wpercent)))
  img = img.resize((pic_width,hsize), Image.ANTIALIAS)
  img.save(path)


def printOutput(inst, dep1, dep2, body, relationships):
  global instPrinted, dep1Printed, dep2Printed, instCount, dep1Count, dep2Count
  
  # Get all project ids of projects that
  #  - have research outcome and 
  #  - where researcher is FROM ${inst}, ${dep1} and ${dep2} and
  #  - the project used the Pan or BeSTGRID cluster
  projects_with_research_outcome = query('SELECT DISTINCT project.id FROM project \
                 INNER JOIN researcher_project rp ON rp.projectId=project.id \
                 INNER JOIN researcher r ON r.id=rp.researcherId \
                   AND r.institution=\'%s\' AND r.division=\'%s\' AND r.department=\'%s\' \
                 INNER JOIN researchoutput ro ON project.id=ro.projectId \
                 INNER JOIN project_facility pf ON project.id=pf.projectId AND (pf.facilityId=1 OR pf.facilityId=5);' % (inst, dep1, dep2))
  # Get all project ids of projects that
  #  - have at least one kpi and 
  #  - where researcher is FROM ${inst}, ${dep1} and ${dep2} and
  #  - the project used the Pan or BeSTGRID cluster
  projects_with_kpis = query('SELECT DISTINCT project.id FROM project \
                 INNER JOIN researcher_project rp ON rp.projectId=project.id \
                 INNER JOIN researcher r ON r.id=rp.researcherId \
                   AND r.institution=\'%s\' AND r.division=\'%s\' AND r.department=\'%s\' \
                 INNER JOIN project_kpi pk ON project.id=pk.projectId \
                 INNER JOIN project_facility pf ON project.id=pf.projectId AND (pf.facilityId=1 OR pf.facilityId=5);' % (inst, dep1, dep2))
  # get unique 'list' of project ids that have either research output or kpis
  pids = set([tmp['id'] for tmp in projects_with_research_outcome] + [tmp['id'] for tmp in projects_with_kpis])

  if not pids:
    return

  for pid in pids:
    # print institution if not already printed
    if instPrinted == 0:
      instCount = instCount + 1
      if skip_formatting:
        str = inst
      else:
        str = '%d. %s' % (instCount, inst)
        str += '\n%s' % (len(str) * '#')
      body.append(heading('%s\n' % str,1))
      body.append(paragraph(''))
      instPrinted = 1
    # print division if not already printed
    if dep1Printed == 0 and dep1 != '':
      dep1Count = dep1Count + 1
      if skip_formatting:
        str = dep1
      else:
        str = '%d.%d. %s' % (instCount, dep1Count, dep1)
        str += '\n%s' % (len(str) * '-') 
      body.append(heading('%s\n' % str,2))
      body.append(paragraph(''))
      dep1Printed = 1
    # print department if not already printed
    if dep2Printed == 0 and dep2 != '':
      dep2Count = dep2Count + 1
      if skip_formatting:
        str = dep2
      else:
        str = '%d.%d.%d. %s' % (instCount, dep1Count, dep2Count, dep2)
        str += '\n%s' % (len(str) * '^') 
      body.append(heading('%s\n\n' % str,3))
      body.append(paragraph(''))
      dep2Printed = 1

    # get title and description for project
    res = query('SELECT name, description FROM project WHERE id=%s' % pid)[0]
    title = res['name'] or 'No title'
    description = res['description'] or 'No description'
    # get name of researchers
    researchers_and_roles = query('SELECT researcher.fullName, pictureUrl, rr.name as role FROM researcher \
                                  INNER JOIN researcher_project rp ON researcher.id=rp.researcherId AND rp.projectId=%s \
                                  INNER JOIN researcherrole rr ON rr.id=rp.researcherRoleId' % pid)
    researcherString = ''
    pictures = paragraph('')
    
    global pic_width
    
    suffix = ''
    
    if len(researchers_and_roles) < 4 :
      pic_width=100
    else :
      pic_width=50
      suffix = '_small'
      
    os.chdir('img')
    
    for researcher_and_role in [tmp for tmp in researchers_and_roles]:
      picpara = None
      filename = researcher_and_role['pictureUrl'].split('/')[-1]
      ext = filename.split('.')[-1]
      filename = filename.split('.')[0]
      if filename != 'avatar' :
        #fetch the image if we don't have it already
        filename = filename + suffix + '.' + ext
        if not os.path.isfile(filename):
          hasDownloaded = downloadAndSaveImage(researcher_and_role['pictureUrl'],filename)
          if hasDownloaded : scaleImage(filename)
        else :
          hasDownloaded = True
        # Generate a picture paragraph if the picture has downloaded
        if hasDownloaded : (relationships, picpara) = picture(relationships, filename, researcher_and_role['fullName'])
      
      if researcher_and_role['role'] == 'Project Owner':
        researcherString += '%s|%s' % (researcher_and_role['fullName'], researcherString)
        if (picpara != None) : 
            picpara.append(pictures)
            pictures = picpara
      else:
        researcherString = '%s|%s' % (researcherString, researcher_and_role['fullName'])
        if (picpara != None) : pictures.append(picpara) 
        
    os.chdir('../')

    #print '%s\n' % (title)
    researchers = researcherString.strip('|').replace('||', ', ').replace('|', ', ')

    # check if the owner of the project is affiliated with the currently processed department
    affil = query('SELECT fullName, institution, division, department from researcher \
                     INNER JOIN researcher_project rp ON researcher.id = rp.researcherId AND rp.projectId=%s \
                     INNER JOIN researcherrole rr ON rr.id = rp.researcherRoleId AND rr.name=\'Project Owner\'' % pid)[0]
    
    outputs=[]
    kpis = ''
    
    if affil['institution'] == inst and affil['division'] == dep1 and affil['department'] == dep2:
      #print 'Description:\n%s\n' % description
      # get ids of research output ordered by output type
      outputIds = query('SELECT id FROM researchoutput WHERE projectId=%s ORDER BY typeId' % pid)
      if outputIds:
        #print 'Research Output:\n'
        
        for outputid in [tmp['id'] for tmp in outputIds]:
          typeName = query('SELECT name FROM researchoutputtype WHERE id=(SELECT typeId FROM researchoutput WHERE id=%s)' % outputid)[0]['name']
          desc = query('SELECT description FROM researchoutput WHERE id=%s' % outputid)[0]['description']
          outputs.append(paragraph(removeNonAscii('%s: %s' % (typeName, desc)),style='ListBullet'))
        #print ''

      # get ids of kpis ordered by kpi id
      
      kpiIds = query('SELECT id FROM project_kpi WHERE projectId=%s ORDER BY kpiId' % pid)
      if kpiIds:
        #print 'Researcher Feedback:\n'
        for kpiId in [tmp['id'] for tmp in kpiIds]:
          res = query('SELECT kpiId, notes FROM project_kpi WHERE id=%s' % kpiId)[0]
          id = res['kpiId']
          notes = res['notes']
          kpis+='%s\n' % notes
    else:
      tmp = '%s, %s, %s' % (affil['institution'], affil['division'], affil['department'])
      #print '(Project description, Research Output and/or KPI information is listed under the PIs (%s) institution (%s))' % (affil['fullName'], tmp.strip().strip(','))
      description = '(Project description, Research Output and/or KPI information is listed under the PIs (%s) institution (%s))' % (affil['fullName'], tmp.strip().strip(','))
   
    # FIXME: Print project information only if project PI is in current affiliation 
    title = heading(removeNonAscii(title),2)
    researchers = heading(removeNonAscii(researchers),5)
    kpis = paragraph([(removeNonAscii(kpis),'i')])
    pictures.append(kpis)
    description = removeNonAscii(description)
    descriptionParagraph = paragraph('')
    
    #split at newline and make a new para for each element
    for d in description.split('\n') :
      descriptionParagraph.append(paragraph(d))
         
    tbl_rows = [[title,researchers],
                [descriptionParagraph,pictures],
                ]
    body.append(table(tbl_rows,
                      borders={'all': {'color': 'grey', 'space': 0, 'sz': 6, 'val': 'single',}},
                      heading=True,
                      headingShade='light1',
                      colw=[80,20],
                      cwunit='pct'))
    
    # if there has been at least one output
    if outputs :
        outputs.append(paragraph('')) #final element must be p
        body.append(table([[outputs]],
                      borders={'all': {'color': 'grey', 'space': 0, 'sz': 6, 'val': 'single',}},
                      heading=True,
                      headingShade='light2'))
          
    body.append(paragraph('\n' * 2))


# main 

instPrinted = dep1Printed = dep2Printed = instCount = dep1Count = dep2Count = 0

# create db connection
db = _mysql.connect(**generate_research_outcomes_and_scalings_docx_example_config.config)

try:
  institutions = query('SELECT DISTINCT institution FROM researcher ORDER BY institution')
  
  # Default set of relationships - the minimum components of a document
  relationships = relationshiplist()
    
  # Make a new document tree - this is the main part of a Word document
  document = newdocument()
    
  # This xpath location is where most interesting content lives
  body = document.xpath('/w:document/w:body', namespaces=nsprefixes)[0]

  # Loop over all institutions, division and department
  for inst in [tmp['institution'] for tmp in institutions]:
    instPrinted = 0
    if inst in blacklist['institutions'] or (len(whitelist['institutions']) > 0 and inst not in whitelist['institutions']):
      continue
    deps1 = query('SELECT DISTINCT division FROM researcher WHERE institution=\'%s\' ORDER BY division' % inst)
    for dep1 in [tmp['division'] for tmp in deps1]:
      if dep1 in blacklist['departments1'] or (len(whitelist['departments1']) > 0 and dep1 not in whitelist['departments1']):
        continue
      dep1Printed = 0
      deps2 = query('SELECT DISTINCT department FROM researcher WHERE institution=\'%s\' AND division=\'%s\' ORDER BY department' % (inst, dep1))
      for dep2 in [tmp['department'] for tmp in deps2]:
        if dep2 in blacklist['departments2'] or (len(whitelist['departments2']) > 0 and dep2 not in whitelist['departments2']):
          continue
        dep2Printed = 0
        printOutput(inst, dep1, dep2, body, relationships)
      dep2Count = 0
    dep1Count = 0
finally:
  db.close()
  

# Create our properties, contenttypes, and other support files
title    = 'Research Outcomes and Outputs'
subject  = 'A report on project statuses'
creator  = 'Center for E-research'
keywords = ['research', 'cer', 'kpis']

coreprops = coreproperties(title=title, subject=subject, creator=creator,
                           keywords=keywords)
appprops = appproperties()
contenttypes = contenttypes()
websettings = websettings()
wordrelationships = wordrelationships(relationships)
filename = 'Reporting_%s.docx' % datetime.now().strftime('%Y-%m-%d_%H-%M')

# Save our document
savedocx(document, coreprops, appprops, contenttypes, websettings,
         wordrelationships, filename)
print 'saved to ' + filename + "\nEnter to quit"
raw_input()
