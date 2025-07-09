from faker import Faker
from random import *

def fake_name(n):
    names = []
    fake = Faker()
    for i in range(n):
        names.append(fake.name())
    return names

def sample_athlete(n):
    names = fake_name(n)
    houses = ['Red','Blue','Green','Yellow']
    sexes   = ['Boys','Girls']
    grades  = ['A','B','C']
    sample_athletes = []
    
    for i in range(1, n):
        aid   = f"ATH{i:03d}"
        name  = names[i]
        x = randint(0, 3)
        y = randint(0, 1)
        z = randint(0, 2)
        house = houses[x]
        sex   = sexes[y]
        grade = grades[z]
        sample_athletes.append((aid, name, house, sex, grade))
    
    return sample_athletes
    
def sample_event():
    arr = ['60 meters','100 meters','200 meters','400 meters','800 meters','1500 meters','High Jump','Long Jump','Shot Put','Javelin','Softball']
    sexes = ['Boys','Girls']
    grades = ['A','B','C']
    
    N = {
      ('60 meters','Boys','A'),('60 meters','Boys','B'),('60 meters','Boys','C'),
      ('60 meters','Girls','A'),
      ('Javelin','Boys','C'),('Javelin','Girls','B'),('Javelin','Girls','C'),
      ('Softball','Boys','A'),('Softball','Boys','B'),('Softball','Girls','A')
    }
    evs = []
    idx = 1
    for e in arr:
      for s in sexes:
        for g in grades:
          if (e,s,g) not in N:
            evs.append( (f"EV{idx:04d}", e, s, g) )
            idx += 1
    return evs
    
def sample(n):
    sample_results = []
    sample_athletes = sample_athlete(n)
    sample_events = sample_event()
    
    for aid,_,_,asex,agrad in sample_athletes:
        for eid,evname,esex,egrade in sample_events:
            if esex == asex and egrade == agrad:
               
                if 'relay' in evname.lower() or 'meters' in evname.lower() and int(evname.split()[0]) >= 800:
                    val = round(uniform(200, 600), 2)  
                elif 'meters' in evname.lower() or 'hurdles' in evname.lower():
                    val = round(uniform(10, 25), 2)    
                elif 'jump' in evname.lower() or 'put' in evname.lower() or 'javelin' in evname.lower():
                    val = round(uniform(1.0, 15.0), 2)
                else:
                    val = round(uniform(10, 100), 2)
                
                sample_results.append((aid, eid, val))
                break
    
    return sample_athletes, sample_events, sample_results
