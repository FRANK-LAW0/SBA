from faker import Faker
from random import *

# generate n random names
def fake_name(n):
    fake = Faker()
    return [fake.name() for _ in range(n)]

# generate information of n athletes
def sample_athlete(n):
    names = fake_name(n)
    houses = ['Red', 'Blue', 'Green', 'Yellow']
    sexes = ['Boys', 'Girls']
    grades = ['A', 'B', 'C']
    sample_athletes = []
    
    for i in range(1, n+1):
        aid = f"ATH{i:03d}"
        name = names[i]
        house = houses[randint(0, 3)]
        sex = sexes[randint(0, 1)]
        grade = grades[randint(0, 2)]
        sample_athletes.append((aid, name, house, sex, grade))
    
    return sample_athletes
    
# generate sample event
def sample_event():
    events = ['60 meters', '100 meters', '200 meters', '400 meters', '800 meters', '1500 meters', 'High Jump', 'Long Jump', 'Shot Put', 'Javelin', 'Softball']
    sexes = ['Boys', 'Girls']
    grades = ['A', 'B', 'C']
    
    excluded_combinations = {
        ('60 meters', 'Boys', 'A'), ('60 meters', 'Boys', 'B'), 
        ('60 meters', 'Boys', 'C'), ('60 meters', 'Girls', 'A'), 
        ('Javelin', 'Boys', 'C'), ('Javelin', 'Girls', 'B'), 
        ('Javelin', 'Girls', 'C'), ('Softball', 'Boys', 'A'), 
        ('Softball', 'Boys', 'B'), ('Softball', 'Girls', 'A')
    }
    
    event_list = []
    idx = 1
    
    for event in events:
        for sex in sexes:
            for grade in grades:
                if (event, sex, grade) not in excluded_combinations:
                    event_list.append((f"EV{idx:04d}", event, sex, grade))
                    idx += 1
    return event_list
  
# generate and return all sample data  
def sample(n):
    sample_results = []
    sample_athletes = sample_athlete(n)
    sample_events = sample_event()
    
    for aid, _, _, asex, agrad in sample_athletes:
        # assume each athlete participates in 3 events
        count = 0
        shuffle(sample_events)
        
        for eid, evname, esex, egrade in sample_events:
            # ensure the sex and grade of athlete match the event
            if esex == asex and egrade == agrad:
                # generate realistic result
                if 'meters' in evname.lower() and int(evname.split()[0]) >= 800:
                    val = round(uniform(200, 600), 2)
                elif 'meters' in evname.lower():
                    val = round(uniform(10, 25), 2)
                elif 'jump' in evname.lower() or 'put' in evname.lower() or 'javelin' in evname.lower():
                    val = round(uniform(1.0, 15.0), 2)
                else:
                    val = round(uniform(10, 100), 2)
                
                sample_results.append((aid, eid, val))
                count += 1
                if count == 3:
                    break
    
    return sample_athletes, sorted(sample_events, key=lambda x: int(x[0][2:6])), sample_results
