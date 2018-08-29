import datetime
import heapq
import math
import pandas
import scipy.stats
import statistics

# assign poll weight based on poll age and type
def pollWeight(age,sample,sampletype):
    pollweight = sample * math.exp(-age / 60.0)
    # adjust poll weight based on poll type
    if sampletype == 'Registered':
        pollweight = pollweight / 2.0
    elif sampletype == 'Internal':
        pollweight = pollweight / 4.0
    elif sampletype == 'Likely':
        pollweight = pollweight
    else:
        raise Exception('Unknown poll type!')
    return pollweight

# assign votes to each party
def votes(weight,dem,gop,ind):
    if math.isnan(dem):
        dem = 0.0
    if math.isnan(gop):
        gop = 0.0
    if math.isnan(ind):
        ind = 0.0
    return  weight*dem,weight*gop,weight*ind

# computes the Cook Partisan Voting Index
def cookPVI(dem1,gop1,dem2,gop2):
    NATIONAL = 0.03075
    dem1_twoparty = dem1 / (dem1+gop1)
    gop1_twoparty = gop1 / (dem1+gop1)
    dem2_twoparty = dem2 / (dem2+gop2)
    gop2_twoparty = gop2 / (dem2+gop2)

    margin1 = dem1_twoparty - gop1_twoparty
    margin2 = dem2_twoparty - gop2_twoparty

    avgmargin = (margin1 + margin2) / 2.0
    return float((avgmargin - NATIONAL) / 2.0 * 100.0)

polldata_file = '/home/jgodwin/Documents/python/python/politimetrics/polldata/senate18_polls.csv'
presdata_file = '/home/jgodwin/Documents/python/python/politimetrics/polldata/presresults.csv'
genericdata_file = '/home/jgodwin/Documents/python/python/politimetrics/polldata/genericballot.csv'
polldata_df = pandas.read_csv(polldata_file)
presdata_df = pandas.read_csv(presdata_file)
generic_df = pandas.read_csv(genericdata_file)
states = polldata_df.State.unique()

senate = ['Arizona','California','Connecticut','Delaware','Florida','Hawaii','Indiana','Maine',\
    'Maryland','Massachusetts','Michigan','Minnesota','Minnesota (S)','Mississippi',\
    'Mississippi (S)','Missouri','Montana','Nebraska','Nevada','New Jersey','New Mexico',\
    'New York','North Dakota','Ohio','Pennsylvania','Rhode Island','Tennessee','Texas','Utah',\
    'Vermont','Virginia','Washington','West Virginia','Wisconsin','Wyoming']

# get the cook PVIs then compute the generic ballot score
generic = {}
polls = {}
for state in senate:
    polls[state] = 0
    race = state
    if '(S)' in state:
        state = state.replace(' (S)','')
    presresults = presdata_df.loc[presdata_df['State']==state]
    pvi = cookPVI(presresults['Clinton'],presresults['Trump'],presresults['Obama'],\
        presresults['Romney'])
    # get the generic ballot polls
    demtotal = 0.0
    goptotal = 0.0
    indtotal = 0.0
    total = 0.0
    pollsters = []
    margins = []
    for index,row in generic_df.iterrows():
        polldate = datetime.datetime.strptime(row['Date'],'%m/%d/%y')
        age = (datetime.datetime.now() - polldate).days
        if age > 60 or row['Poll'] in pollsters:
            continue
        pollsters.append(row['Poll'])
        # determine how much weight to give the poll, but don't give it over 1000
        pollweight = min(pollWeight(age,row['Sample'],row['Type']),1000)
        # get number of votes for each candidate
        demvotes,gopvotes,indvotes = votes(pollweight,row['DEM']/100.0,row['GOP']/100.0,0.0)
        margins.append(row['DEM']/100.0 - row['GOP']/100.0)
        undvotes = pollweight - (demvotes + gopvotes + indvotes)
        # assign undecided votes
        demvotes_und,gopvotes_und,indvotes_und = votes(undvotes,row['DEM']/100.0,row['GOP']/100.0,0.0)
        # add up all votes
        demtotal += (demvotes + demvotes_und)
        goptotal += (gopvotes + gopvotes_und)
        indtotal += (indvotes + indvotes_und)
        total = (demtotal + goptotal + indtotal)
    # *** generic score ***
    generic[race] = pvi/50.0 + (demtotal/total - goptotal/total)
    genericstdev = statistics.stdev(margins)

# get the polling data and compute the polling score
stateaverage = {}
statemargin = {}
statestdevs = {}
for state in states:
    statepolls = polldata_df.loc[polldata_df['State']==state]
    demtotal = 0.0
    goptotal = 0.0
    indtotal = 0.0
    total = 0.0
    pollsters = []
    margins = []
    # loop through each poll by state
    for index,row in statepolls.iterrows():
        # get poll age
        polldate = datetime.datetime.strptime(row['Date'],'%m/%d/%y')
        age = (datetime.datetime.now() - polldate).days
        if age > 60 or row['Poll'] in pollsters:
            continue
        polls[state] += 1
        pollsters.append(row['Poll'])
        # determine how much weight to give the poll, but don't give it over 1000
        pollweight = min(pollWeight(age,row['Sample'],row['Type']),1000)
        # get number of votes for each candidate
        demvotes,gopvotes,indvotes = votes(pollweight,row['DEM']/100.0,row['GOP']/100.0,row['IND']/100.0)
        # check to see if the independent candidate is in first or second place
        if not math.isnan(row['IND']) and row['IND'] >= heapq.nlargest(2,[row['DEM'],row['GOP'],row['IND']])[-1]:
            # independent vs. republican
            if row['GOP'] > row['DEM'] or math.isnan(row['DEM']):
                margins.append(row['IND']/100.0 - row['GOP']/100.0)
            # independent vs. democrat
            else:
                margins.append(row['DEM']/100.0 - row['IND']/100.0)
        else:
            margins.append(row['DEM']/100.0 - row['GOP']/100.0)
        undvotes = pollweight - (demvotes + gopvotes + indvotes)
        # assign undecided votes
        demvotes_und,gopvotes_und,indvotes_und = votes(undvotes,row['DEM']/100.0,row['GOP']/100.0,row['IND']/100.0)
        # add up all votes
        demtotal += (demvotes + demvotes_und)
        goptotal += (gopvotes + gopvotes_und)
        indtotal += (indvotes + indvotes_und)
        total = (demtotal + goptotal + indtotal)
    if total != 0:
        stateaverage[state] = [demtotal/total,goptotal/total,indtotal/total]
        # *** polling score ***
        # check to see if there is a major independent candidate
        if not math.isnan(indtotal) and indtotal >= heapq.nlargest(2,[demtotal,goptotal,indtotal])[-1]:
            # independent vs. republican
            if goptotal > demtotal or math.isnan(demtotal):
                statemargin[state] = indtotal/total - goptotal/total
            # independent vs. democrat
            else:
                statemargin[state] = demtotal/total - indtotal/total
        # democrat vs. republican
        else: 
            statemargin[state] = (demtotal/total - goptotal/total)

        # get the standard deviations
        if len(margins) > 1:
            statestdevs[state] = statistics.stdev(margins)
        else:
            statestdevs[state] = genericstdev

# *** forecast margin ***
for state in senate:
    if state in statemargin.keys():
        forecast = (4.0*statemargin[state] + generic[state]) / 5.0
    else:
        forecast = generic[state]

    # forecast by party
    dem_fcst = 0.5 + forecast/2.0
    gop_fcst = 0.5 - forecast/2.0

    # probabilities and final results
    if state not in statestdevs or statestdevs[state] == 0:
        statestdevs[state] = genericstdev
    dem_prob = scipy.stats.norm(0.5,statestdevs[state]).cdf(dem_fcst)
    gop_prob = scipy.stats.norm(0.5,statestdevs[state]).cdf(gop_fcst)
    if polls[state] == 0:
        print('%s - Democratic: %.1f%%, Republican: %.1f%% - WARNING: NO RECENT POLLS' % (state,dem_prob*100,gop_prob*100))
    else:
        print('%s - Democratic: %.1f%%, Republican: %.1f%%' % (state,dem_prob*100,gop_prob*100))

