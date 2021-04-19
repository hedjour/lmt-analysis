'''
Created on 13 sept. 2017

@author: Fab
'''

import sqlite3
from lmtanalysis.Animal import *
import numpy as np
import matplotlib.pyplot as plt
from lmtanalysis.Event import *
from lmtanalysis.Measure import *
import colorsys
from collections import Counter
import seaborn as sns
import matplotlib.patches as mpatches


from tkinter.filedialog import askopenfilename
from lmtanalysis.Util import getMinTMaxTAndFileNameInput
from lmtanalysis.EventTimeLineCache import EventTimeLineCached
from lmtanalysis.FileUtil import getFilesToProcess, getJsonFileToProcess
from lmtanalysis.Util import getFileNameInput, getStarsFromPvalues
import statsmodels.api as sm
import statsmodels.formula.api as smf
import pandas
from scipy.stats import mannwhitneyu, kruskal, ttest_1samp

def computeProfile(file, minT, maxT, night, text_file):
    
    connection = sqlite3.connect( file )
    
    pool = AnimalPool( )
    pool.loadAnimals( connection )
    
    animalData = {}
    
    for animal in pool.animalDictionnary.keys():
        
        print( "computing individual animal: {}".format( animal ))
        rfid = pool.animalDictionnary[animal].RFID
        print( "RFID: {}".format( rfid ) )
        animalData[rfid]= {}        
        #store the animal
        animalData[rfid]["animal"] = pool.animalDictionnary[animal].name
        animalObject = pool.animalDictionnary[animal]
        animalData[rfid]["file"] = file
        animalData[rfid]['genotype'] = pool.animalDictionnary[animal].genotype
                
        genoA = None
        try:
            genoA=pool.animalDictionnary[animal].genotype
        except:
            pass
                    
        for behavEvent in behaviouralEventOneMouse[:-2]:
            
            print( "computing individual event: {}".format(behavEvent))    
            
            behavEventTimeLine = EventTimeLineCached( connection, file, behavEvent, animal, minFrame=minT, maxFrame=maxT )
            
            totalEventDuration = behavEventTimeLine.getTotalLength()
            nbEvent = behavEventTimeLine.getNumberOfEvent(minFrame = minT, maxFrame = maxT )
            print( "total event duration: " , totalEventDuration )                
            animalData[rfid][behavEventTimeLine.eventName+" TotalLen"] = totalEventDuration
            animalData[rfid][behavEventTimeLine.eventName+" Nb"] = nbEvent
            if nbEvent == 0:
                meanDur = 0
            else:
                meanDur = totalEventDuration / nbEvent
            animalData[rfid][behavEventTimeLine.eventName+" MeanDur"] = meanDur
            
            print(behavEventTimeLine.eventName, genoA, behavEventTimeLine.idA, totalEventDuration, nbEvent, meanDur)

        #compute the total distance traveled
        COMPUTE_TOTAL_DISTANCE = True
        if ( COMPUTE_TOTAL_DISTANCE == True ):
            animalObject.loadDetection( start=minT, end=maxT, lightLoad = True )
            animalData[rfid]["totalDistance"] = animalObject.getDistance( tmin=minT,tmax=maxT)/100
        else:
            animalData[rfid]["totalDistance"] = "totalDistance"


    header = ["file", "strain", "sex", "group", "day", "exp", "RFID", "genotype", "user1", "minTime", "maxTime"]
    for name in header:
        text_file.write("{}\t".format(name))

    #write event keys
    firstAnimalKey = next(iter(animalData))
    firstAnimal = animalData[firstAnimalKey]
    for k in firstAnimal.keys():
        text_file.write( "{}\t".format( k.replace(" ", "") ) )
    text_file.write("\n")
    
    for kAnimal in animalData:
        text_file.write( "{}\t".format( file ) )
        text_file.write( "{}\t".format( "strain" ) )
        text_file.write( "{}\t".format( "sex" ) )
        text_file.write( "{}\t".format( "group" ) )
        text_file.write( "{}\t".format( night ) )
        text_file.write( "{}\t".format( "exp" ) )
        text_file.write( "{}\t".format( kAnimal ) )
        text_file.write( "{}\t".format( animalData[kAnimal]["genotype"] ) )
        text_file.write( "{}\t".format( minT ) )
        text_file.write( "{}\t".format( maxT ) )

        for kEvent in firstAnimal.keys():
            text_file.write( "{}\t".format( animalData[kAnimal][kEvent] ) )
        text_file.write( "\n" )
        
    return animalData


def getProfileValues( profileData, night='0', event=None):
    dataDic = {}
    dataDic["genotype"] = []
    dataDic["value"] = []
    dataDic["exp"] = []
    
    for file in profileData.keys():
        print(profileData[file].keys())
        for animal in profileData[file][str(night)].keys():
            dataDic["value"].append(profileData[file][str(night)][animal][event])
            dataDic["exp"].append(profileData[file][str(night)][animal]["file"])
            dataDic["genotype"].append(profileData[file][str(night)][animal]["genotype"])
    
    return dataDic


def plotProfileDataDuration(profileData, night, valueCat):
    fig, axes = plt.subplots(nrows=5, ncols=6, figsize=(14, 12))
    
    row=0
    col=0
    fig.suptitle(t="{} of events (night {})".format(valueCat, night), y=1.2, fontweight= 'bold')
    
    #plot the data for each behavioural event
    for behavEvent in behaviouralEventOneMouse[:-2]:
        event = behavEvent+valueCat
        print("event: ", event)
        
        profileValueDictionary = getProfileValues(profileData=profileData, night=night, event=event)
        y = profileValueDictionary["value"]
        x = profileValueDictionary["genotype"]
        genotypeType = Counter(x)
        group = profileValueDictionary["exp"]
        
        print("y: ", y)
        print("x: ", x)
        print("group: ", group)
        experimentType = Counter(group)
        print("Nb of experiments: ", len(experimentType))
        
        axes[row,col].set_xlim(-0.5, 1.5)
        axes[row,col].set_ylim(min(y)-0.2*max(y), max(y)+0.2*max(y))
        sns.stripplot(x, y, jitter=True, hue=group, s=5, ax=axes[row,col] )
        axes[row,col].set_title(behavEvent)
        axes[row,col].set_ylabel("{} (frames)".format(valueCat))
        axes[row,col].legend().set_visible(False)
        axes[row,col].spines['right'].set_visible(False)
        axes[row,col].spines['top'].set_visible(False)
        
        if col<5:
            col+=1
            row=row
        else:
            col=0
            row+=1
    
    #plot the data for the total distance traveled   
    profileValueDictionary = getProfileValues(profileData=profileData, night=night, event="totalDistance")
    y = profileValueDictionary["value"]
    x = profileValueDictionary["genotype"]
    genotypeType = Counter(x)
    group = profileValueDictionary["exp"]
    
    print("y: ", y)
    print("x: ", x)
    print("group: ", group)
    experimentType = Counter(group)
    print("Nb of experiments: ", len(experimentType))
    
    axes[row,col].set_xlim(-0.5, 1.5)
    axes[row,col].set_ylim(min(y)-0.2*max(y), max(y)+0.2*max(y))
    sns.stripplot(x, y, jitter=True, hue=group, s=5, ax=axes[row,col] )
    axes[row,col].set_title("Activity")
    axes[row,col].set_ylabel("total distance (m)")
    axes[row,col].legend().set_visible(False)
    axes[row,col].spines['right'].set_visible(False)
    axes[row,col].spines['top'].set_visible(False)
    
    if col<7:
        col+=1
        row=row
    else:
        col=0
        row+=1
    
    fig.tight_layout()    
    fig.savefig( "FigProfile{}_Events_night_{}.pdf".format( valueCat, night ) ,dpi=100)
    plt.close( fig )
    

def testProfileData(profileData=None, night=0, eventListNames=None, valueCat="", text_file=None):
    for behavEvent in eventListNames:
        event = behavEvent+valueCat
        print("event: ", event)
        text_file.write("Test for the event: {} night {}".format( event, night ) )
        
        profileValueDictionary = getProfileValues(profileData=profileData, night=night, event=event)
        
        dfData = pandas.DataFrame({'group': profileValueDictionary["exp"],
                                   'genotype': profileValueDictionary["genotype"],
                                   'value': profileValueDictionary["value"]})
        
        #pandas.DataFrame(dfData).info()
        #Mixed model: variable to explain: value; fixed factor = genotype; random effect: group
        #create model:
        model = smf.mixedlm("value ~ genotype", dfData, groups = dfData["group"])
        #run model: 
        result = model.fit()
        #print summary
        print(result.summary())
        text_file.write(result.summary().as_text())
        text_file.write('\n')

def mergeProfileOverNights( profileData, categoryList ):
    #merge data from the different nights
    mergeProfile = {}
    for file in profileData.keys():
        nightList = list( profileData[file].keys() )
        mergeProfile[file] = {}
        mergeProfile[file]['all nights'] = {}
        for rfid in profileData[file][nightList[0]].keys():
            mergeProfile[file]['all nights'][rfid] = {}
            mergeProfile[file]['all nights'][rfid]['animal'] = profileData[file][nightList[0]][rfid]['animal']
            mergeProfile[file]['all nights'][rfid]['genotype'] = profileData[file][nightList[0]][rfid]['genotype']
            mergeProfile[file]['all nights'][rfid]['file'] = profileData[file][nightList[0]][rfid]['file']
            for cat in categoryList:
                traitList = [trait+cat for trait in behaviouralEventOneMouse[:-2]]
                for event in traitList:
                    dataNight = 0
                    for night in profileData[file].keys():
                        dataNight += profileData[file][night][rfid][event]

                    if ' MeanDur' in event:
                        mergeProfile[file]['all nights'][rfid][event] = dataNight / len(profileData[file].keys())
                    else:
                        mergeProfile[file]['all nights'][rfid][event] = dataNight

            distNight = 0
            for night in profileData[file].keys():
                distNight += profileData[file][night][rfid]['totalDistance']

            mergeProfile[file]['all nights'][rfid]['totalDistance'] = distNight
    return mergeProfile

def extractControlData(profileData, genoControl):
    categoryList = [' TotalLen', ' Nb', ' MeanDur']
    nightList = list(profileData[list(profileData.keys())[0]].keys())
    print('nights: ', nightList)

    wtData = {}
    for file in profileData.keys():
        wtData[file] = {}
        for night in nightList:
            wtData[file][night] = {}
            temporaryWT = {}
            for cat in categoryList:
                traitList = [trait + cat for trait in behaviouralEventOneMouse[:-2]]
                for event in traitList:
                    temporaryWT[event] = []
            temporaryWT['totalDistance'] = []

            for rfid in profileData[file][night].keys():
                if profileData[file][night][rfid]['genotype'] == genoControl:
                    temporaryWT['totalDistance'].append(profileData[file][night][rfid]['totalDistance'])
                    for cat in categoryList:
                        traitList = [trait + cat for trait in behaviouralEventOneMouse[:-2]]
                        for event in traitList:
                            temporaryWT[event].append(profileData[file][night][rfid][event])

            wtData[file][night]['mean totalDistance'] = np.mean(temporaryWT['totalDistance'])
            wtData[file][night]['std totalDistance'] = np.std(temporaryWT['totalDistance'])
            for cat in categoryList:
                traitList = [trait + cat for trait in behaviouralEventOneMouse[:-2]]
                for event in traitList:
                    wtData[file][night]['mean ' + event] = np.mean(temporaryWT[event])
                    wtData[file][night]['std ' + event] = np.std(temporaryWT[event])
    return wtData

def extractCageData(profileData):
    categoryList = [' TotalLen', ' Nb', ' MeanDur']
    nightList = list(profileData[list(profileData.keys())[0]].keys())
    print('nights: ', nightList)

    wtData = {}
    for file in profileData.keys():
        wtData[file] = {}
        for night in nightList:
            wtData[file][night] = {}
            temporaryWT = {}
            for cat in categoryList:
                traitList = [trait + cat for trait in behaviouralEventOneMouse[:-2]]
                for event in traitList:
                    temporaryWT[event] = []
            temporaryWT['totalDistance'] = []

            for rfid in profileData[file][night].keys():
                temporaryWT['totalDistance'].append(profileData[file][night][rfid]['totalDistance'])
                for cat in categoryList:
                    traitList = [trait + cat for trait in behaviouralEventOneMouse[:-2]]
                    for event in traitList:
                        temporaryWT[event].append(profileData[file][night][rfid][event])

            wtData[file][night]['mean totalDistance'] = np.mean(temporaryWT['totalDistance'])
            wtData[file][night]['std totalDistance'] = np.std(temporaryWT['totalDistance'])
            for cat in categoryList:
                traitList = [trait + cat for trait in behaviouralEventOneMouse[:-2]]
                for event in traitList:
                    wtData[file][night]['mean ' + event] = np.mean(temporaryWT[event])
                    wtData[file][night]['std ' + event] = np.std(temporaryWT[event])
    return wtData


def generateMutantData(profileData, genoMutant, wtData, categoryList, behaviouralEventOneMouse):
    nightList = list(profileData[list(profileData.keys())[0]].keys())
    print('nights: ', nightList)

    koData = {}
    for file in profileData.keys():
        koData[file] = {}
        for night in nightList:
            koData[file][night] = {}
            temporaryKO = {}
            for cat in categoryList:
                traitList = [trait + cat for trait in behaviouralEventOneMouse[:-2]]
                for event in traitList:
                    temporaryKO[event] = []
            temporaryKO['totalDistance'] = []

            for rfid in profileData[file][night].keys():
                if profileData[file][night][rfid]['genotype'] == genoMutant:
                    koData[file][night][rfid] = {}
                    koData[file][night][rfid]['totalDistance'] = (profileData[file][night][rfid]['totalDistance'] - wtData[file][night]['mean totalDistance']) / wtData[file][night]['std totalDistance']
                    for cat in categoryList:
                        traitList = [trait + cat for trait in behaviouralEventOneMouse[:-2]]
                        for event in traitList:
                            koData[file][night][rfid][event] = (profileData[file][night][rfid][event] - wtData[file][night]['mean ' + event]) / wtData[file][night]['std '+ event]

    return koData

if __name__ == '__main__':
    
    print("Code launched.")
    # set font
    from matplotlib import rc, gridspec

    rc('font', **{'family': 'serif', 'serif': ['Arial']})
    #List of events to be computed within the behavioural profile2, and header for the computation of the total distance travelled.
    behaviouralEventOneMouse = ["Contact", "Oral-oral Contact", "Oral-genital Contact", "Side by side Contact", "Side by side Contact, opposite way", "Social approach", "Get away", "Approach contact", "Approach rear", "Break contact", "FollowZone Isolated", "Train2", "Group2", "Group3", "Group 3 break", "Group 3 make", "Group 4 break", "Group 4 make", "Huddling", "Move isolated", "Move in contact", "Nest3_", "Nest4_", "Rearing", "Rear isolated", "Rear in contact", "Stop isolated", "WallJump", "Water Zone", "totalDistance", "experiment"]
    behaviouralEventOneMouse = ["Move isolated", "Move in contact", "WallJump", "Stop isolated", "Rear isolated", "Rear in contact",
    "Contact", "Group2", "Group3", "Oral-oral Contact", "Oral-genital Contact", "Side by side Contact", "Side by side Contact, opposite way",
    "Train2", "FollowZone Isolated",
    "Social approach", "Approach contact",
    "Group 3 make", "Group 4 make", "Get away", "Break contact",
    "Group 3 break", "Group 4 break",
    "totalDistance", "experiment"
    ]
    #behaviouralEventOneMouse = ["Contact", "Oral-genital Contact", "totalDistance", "experiment"]

    while True:

        question = "Do you want to:"
        question += "\n\t [c]ompute profile data (save json file)?"
        question += "\n\t [p]lot and analyse profile data (from stored json file)?"
        question += "\n\t [pn]lot and analyse profile data after merging the different nigths?"
        question += "\n\t [prof] plot KO profile data as centered and reduced data per cage?"
        question += "\n"
        answer = input(question)

        if answer == "c":
            files = getFilesToProcess()
            tmin, tmax, text_file = getMinTMaxTAndFileNameInput()

            profileData = {}
            nightComputation = input("Compute profile only during night events (Y or N)? ")

            for file in files:

                print(file)
                connection = sqlite3.connect( file )

                profileData[file] = {}

                pool = AnimalPool( )
                pool.loadAnimals( connection )

                if nightComputation == "N":
                    minT = tmin
                    maxT = tmax
                    n = 0
                    #Compute profile2 data and save them in a text file
                    profileData[file][n] = computeProfile(file = file, minT=minT, maxT=maxT, night=n, text_file=text_file)
                    text_file.write( "\n" )
                    # Create a json file to store the computation
                    with open("profile_data_{}.json".format('no_night'), 'w') as fp:
                        json.dump(profileData, fp, indent=4)
                    print("json file with profile measurements created.")


                else:
                    nightEventTimeLine = EventTimeLineCached( connection, file, "night", minFrame=tmin, maxFrame=tmax )
                    n = 1

                    for eventNight in nightEventTimeLine.getEventList():
                        minT = eventNight.startFrame
                        maxT = eventNight.endFrame
                        print("Night: ", n)
                        #Compute profile2 data and save them in a text file
                        profileData[file][n] = computeProfile(file=file, minT=minT, maxT=maxT, night=n, text_file=text_file)
                        text_file.write( "\n" )
                        n+=1
                        print("Profile data saved.")

                    # Create a json file to store the computation
                    with open("profile_data_{}.json".format('over_night'), 'w') as fp:
                        json.dump(profileData, fp, indent=4)
                    print("json file with profile measurements created.")

            text_file.write( "\n" )
            text_file.close()

            break

        if answer == "p":
            nightComputation = input("Plot profile only during night events (Y or N)? ")
            text_file = getFileNameInput()

            if nightComputation == "N":
                n = 0
                file = getJsonFileToProcess()
                print(file)
                # create a dictionary with profile data
                with open(file) as json_data:
                    profileData = json.load(json_data)

                print("json file for profile data re-imported.")
                #Plot profile2 data and save them in a pdf file
                print('data: ', profileData)
                plotProfileDataDuration(profileData=profileData, night=n, valueCat=" TotalLen")
                plotProfileDataDuration(profileData=profileData, night=n, valueCat=" Nb")
                plotProfileDataDuration(profileData=profileData, night=n, valueCat=" MeanDur")
                text_file.write( "Statistical analysis: mixed linear models" )
                text_file.write( "{}\n" )
                #Test profile2 data and save results in a text file
                testProfileData(profileData=profileData, night=n, eventListNames=behaviouralEventOneMouse[:-2], valueCat=" TotalLen", text_file=text_file)
                testProfileData(profileData=profileData, night=n, eventListNames=behaviouralEventOneMouse[:-2], valueCat=" Nb", text_file=text_file)
                testProfileData(profileData=profileData, night=n, eventListNames=behaviouralEventOneMouse[:-2], valueCat=" MeanDur", text_file=text_file)

                print("test for total distance")
                testProfileData(profileData=profileData, night=n, eventListNames=["totalDistance"], valueCat="", text_file=text_file)

            elif nightComputation == "Y":
                file = getJsonFileToProcess()
                # create a dictionary with profile data
                with open(file) as json_data:
                    profileData = json.load(json_data)
                print("json file for profile data re-imported.")

                nightList = list(profileData[list(profileData.keys())[0]].keys())
                print('nights: ', nightList)

                for n in nightList:

                    print("Night: ", n)
                    #Plot profile2 data and save them in a pdf file
                    plotProfileDataDuration(profileData=profileData, night=str(n), valueCat=" TotalLen")
                    plotProfileDataDuration(profileData=profileData, night=str(n), valueCat=" Nb")
                    plotProfileDataDuration(profileData=profileData, night=str(n), valueCat=" MeanDur")
                    text_file.write( "Statistical analysis: mixed linear models" )
                    text_file.write( "{}\n" )
                    #Test profile2 data and save results in a text file
                    testProfileData(profileData=profileData, night=str(n), eventListNames=behaviouralEventOneMouse[:-2], valueCat=" TotalLen", text_file=text_file)
                    testProfileData(profileData=profileData, night=str(n), eventListNames=behaviouralEventOneMouse[:-2], valueCat=" Nb", text_file=text_file)
                    testProfileData(profileData=profileData, night=str(n), eventListNames=behaviouralEventOneMouse[:-2], valueCat=" MeanDur", text_file=text_file)

                    print("test for total distance")
                    testProfileData(profileData=profileData, night=str(n), eventListNames=["totalDistance"], valueCat="", text_file=text_file)



            print ("Plots saved as pdf and analyses saved in text file.")

            text_file.close()
            break

        if answer == "pn":
            print('Choose the profile json file to process.')
            file = getJsonFileToProcess()
            # create a dictionary with profile data
            with open(file) as json_data:
                profileData = json.load(json_data)
            print("json file for profile data re-imported.")

            print('Choose a name for the text file to store analyses results.')
            text_file = getFileNameInput()

            nightList = list(profileData[list(profileData.keys())[0]].keys())
            print('nights: ', nightList)

            categoryList = [' TotalLen', ' Nb', ' MeanDur']

            mergeProfile = mergeProfileOverNights( profileData=profileData, categoryList=categoryList )

            n = 'all nights'

            plotProfileDataDuration(profileData=mergeProfile, night=n, valueCat=" TotalLen")
            plotProfileDataDuration(profileData=mergeProfile, night=n, valueCat=" Nb")
            plotProfileDataDuration(profileData=mergeProfile, night=n, valueCat=" MeanDur")
            text_file.write("Statistical analysis: mixed linear models")
            text_file.write("{}\n")
            # Test profile data and save results in a text file
            testProfileData(profileData=mergeProfile, night=n, eventListNames=behaviouralEventOneMouse[:-2],
                            valueCat=" TotalLen", text_file=text_file)
            testProfileData(profileData=mergeProfile, night=n, eventListNames=behaviouralEventOneMouse[:-2],
                            valueCat=" Nb", text_file=text_file)
            testProfileData(profileData=mergeProfile, night=n, eventListNames=behaviouralEventOneMouse[:-2],
                            valueCat=" MeanDur", text_file=text_file)

            print("test for total distance")
            testProfileData(profileData=mergeProfile, night=n, eventListNames=["totalDistance"], valueCat="",
                            text_file=text_file)


            text_file.close()
            print('Job done.')

            break


        if answer == "prof":
            print('Choose the profile json file to process.')
            file = getJsonFileToProcess()
            # create a dictionary with profile data
            with open(file) as json_data:
                profileData = json.load(json_data)
            print("json file for profile data re-imported.")
            categoryList = [' TotalLen', ' Nb', ' MeanDur']

            mergeProfile = mergeProfileOverNights( profileData=profileData, categoryList=categoryList )
            #If the profiles are computed over the nights separately as in the original json file:
            #dataToUse = profileData
            #If the profiles are computed over the merged nights:
            dataToUse = mergeProfile

            #compute the data for the control animal of each cage
            genoControl = 'WT'
            wtData = extractControlData( profileData=dataToUse, genoControl=genoControl)
            wtData = extractCageData(profileData=dataToUse)
            #mergeProfile = mergeProfileOverNights(profileData=profileData, categoryList=categoryList )
            #wtData = extractControlData(profileData=mergeProfile, genoControl=genoControl)
            #print(wtData)

            #compute the mutant data, centered and reduced for each cage
            genoMutant = 'Del/+'
            koData = generateMutantData(profileData=dataToUse, genoMutant=genoMutant, wtData=wtData, categoryList=categoryList, behaviouralEventOneMouse=behaviouralEventOneMouse )

            print(koData)

            for cat in categoryList:
                fig, axes = plt.subplots(nrows=1, ncols=3, figsize=(24, 12), sharey=True)

                koDataDic = {}
                for key in ['night', 'trait', 'rfid', 'exp', 'value']:
                    koDataDic[key] = []

                for file in koData.keys():
                    for night in koData[file].keys():
                        for rfid in koData[file][night].keys():
                            eventListForTest = []
                            for event in koData[file][night][rfid].keys():
                                if (cat in event) or (event=='totalDistance'):
                                    koDataDic['exp'].append(file)
                                    koDataDic['night'].append(night)
                                    koDataDic['rfid'].append(rfid)
                                    koDataDic['trait'].append(event)
                                    koDataDic['value'].append(koData[file][night][rfid][event])
                                    eventListForTest.append(event)
                #print(koDataDic)

                koDataframe = pd.DataFrame.from_dict(koDataDic)
                #print(koDataframe)

                nightList = list(koData[list(koData.keys())[0]].keys())



                row = 0
                for night in nightList:
                    ax = axes[row]
                    selectedDataframe = koDataframe[(koDataframe['night'] == night)]
                    pos = 0
                    for event in eventListForTest:
                        valList = selectedDataframe['value'][selectedDataframe['trait']==event]
                        T, p = ttest_1samp( valList, popmean=0 )
                        if p < 0.05:
                            print(night, event, T, p)
                            ax.text(-2.95, pos, s=getStarsFromPvalues(p, numberOfTests=1), fontsize=16)
                        pos += 1


                    #ax.set_xlim(-0.5, 1.5)
                    #ax.set_ylim(min(selectedDataframe['value']) - 0.2 * max(selectedDataframe['value']), max(selectedDataframe['value']) + 0.2 * max(selectedDataframe['value']))
                    ax.set_xlim(-3, 3)
                    ax.spines['right'].set_visible(False)
                    ax.spines['top'].set_visible(False)
                    ax.legend().set_visible(False)
                    ax.set_title('night {}'.format(night))

                    ax.add_patch(mpatches.Rectangle((-3, -1), width=6, height=5.3, facecolor='grey', alpha=0.3))
                    ax.text(-2.6, 2.1, s='ACTIVITY', color='white', fontsize=14, fontweight='bold', rotation='vertical', verticalalignment='center')

                    ax.add_patch(mpatches.Rectangle((-3, 4.6), width=6, height=1.7, facecolor='grey', alpha=0.3))
                    ax.text(-2.6, 5.5, s='EXPLO', color='white', fontsize=14, fontweight='bold', rotation='vertical',
                            verticalalignment='center')

                    ax.add_patch(mpatches.Rectangle((-3, 6.6), width=6, height=6.7, facecolor='grey', alpha=0.3))
                    ax.text(-2.6, 9.6, s='CONTACT', color='white', fontsize=14, fontweight='bold', rotation='vertical',
                            verticalalignment='center')

                    ax.add_patch(mpatches.Rectangle((-3, 13.6), width=6, height=1.7, facecolor='grey', alpha=0.3))
                    ax.text(-2.6, 14.5, s='FOLLOW', color='white', fontsize=14, fontweight='bold', rotation='vertical',
                            verticalalignment='center')

                    ax.add_patch(mpatches.Rectangle((-3, 15.6), width=6, height=3.7, facecolor='grey', alpha=0.3))
                    ax.text(-2.6, 17.4, s='APPROACH', color='white', fontsize=14, fontweight='bold', rotation='vertical',
                            verticalalignment='center')

                    ax.add_patch(mpatches.Rectangle((-3, 19.6), width=6, height=3.7, facecolor='grey', alpha=0.3))
                    ax.text(-2.6, 21.6, s='ESCAPE', color='white', fontsize=14, fontweight='bold', rotation='vertical',
                            verticalalignment='center')

                    meanprops = dict(marker='D', markerfacecolor='white', markeredgecolor='black')
                    bp = sns.boxplot( data=selectedDataframe, y='trait', x='value', ax=ax, width=0.5, orient='h', meanprops=meanprops, showmeans=True, linewidth=0.4 )
                    sns.swarmplot(data=selectedDataframe, y='trait', x='value', ax=ax, color='black', orient='h')
                    #this swarmplot should be used instead of the previous one if you want to see whether animals from the same cage are similar
                    #sns.swarmplot(data=selectedDataframe, y='trait', x='value', ax=ax, hue='exp', orient='h')
                    ax.vlines(x=0, ymin=-6, ymax=30, colors='grey', linestyles='dashed')
                    ax.vlines(x=-1, ymin=-1, ymax=30, colors='grey', linestyles='dotted')
                    ax.vlines(x=1, ymin=-1, ymax=30, colors='grey', linestyles='dotted')

                    ax.set_xlabel('Z-score per cage', fontsize=18)
                    ax.set_ylabel('Behavioral events', fontsize=18)

                    ax.set_yticklabels(eventListForTest, rotation=0, FontSize=14,
                                       horizontalalignment='right')
                    ax.set_xticklabels([-3, -2, -1, 0, 1, 2, 3], FontSize=14)
                    ax.legend().set_visible(False)
                    row += 1

                plt.tight_layout()
                plt.show()
                fig.savefig('profiles_zscores_{}.pdf'.format(cat), dpi=300)

            print('Job done.')

            break
            
            