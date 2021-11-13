import toontown.minigame.MinigameCreatorAI
from toontown.distributed.ToontownDistrictAI import ToontownDistrictAI
from toontown.distributed.ToontownDistrictStatsAI import ToontownDistrictStatsAI
from otp.ai.TimeManagerAI import TimeManagerAI
from otp.ai.MagicWordManagerAI import MagicWordManagerAI
from toontown.ai.HolidayManagerAI import HolidayManagerAI
from toontown.ai.NewsManagerAI import NewsManagerAI
from toontown.ai.FishManagerAI import FishManagerAI
from toontown.ai.QuestManagerAI import QuestManagerAI
from toontown.safezone.SafeZoneManagerAI import SafeZoneManagerAI
from toontown.distributed.ToontownInternalRepository import ToontownInternalRepository
from toontown.toon import NPCToons
from toontown.hood import TTHoodAI, DDHoodAI, DGHoodAI, BRHoodAI, MMHoodAI, DLHoodAI, OZHoodAI, GSHoodAI, GZHoodAI, ZoneUtil
from toontown.hood import SellbotHQAI, CashbotHQAI, LawbotHQAI, BossbotHQAI
from toontown.toonbase import ToontownGlobals
from direct.distributed.PyDatagram import *
from otp.ai.AIZoneData import *
from toontown.dna.DNAParser import loadDNAFileAI
from toontown.coghq import MintManagerAI, FactoryManagerAI, LawOfficeManagerAI, CountryClubManagerAI
from toontown.pets import PetManagerAI
from toontown.ai import CogSuitManagerAI
from toontown.ai import PromotionManagerAI
from toontown.building.DistributedTrophyMgrAI import DistributedTrophyMgrAI

#friends!
from otp.friends.FriendManagerAI import FriendManagerAI

#estates
from toontown.estate.EstateManagerAI import EstateManagerAI

# par-tay
from toontown.uberdog.DistributedPartyManagerAI import DistributedPartyManagerAI
from otp.distributed.OtpDoGlobals import *

# All imports needed for fireworks
from direct.task import Task
from toontown.toonbase import ToontownGlobals
from toontown.effects.DistributedFireworkShowAI import DistributedFireworkShowAI
from toontown.effects import FireworkShows
import random
from direct.distributed.ClockDelta import *
import time
from otp.ai.MagicWordGlobal import *
from toontown.parties import PartyGlobals

class ToontownAIRepository(ToontownInternalRepository):
    def __init__(self, baseChannel, serverId, districtName):
        ToontownInternalRepository.__init__(self, baseChannel, serverId, dcSuffix='AI')

        self.districtName = districtName
        self.notify.setInfo(True)

        self.zoneAllocator = UniqueIdAllocator(ToontownGlobals.DynamicZonesBegin,
                                               ToontownGlobals.DynamicZonesEnd)

        NPCToons.generateZone2NpcDict()

        self.hoods = []
        self.zoneDataStore = AIZoneDataStore()

        self.wantCogdominiums = self.config.GetBool('want-cogdominiums', False)
        self.useAllMinigames = self.config.GetBool('want-all-minigames', False)
        self.doLiveUpdates = False

        self.questManager = QuestManagerAI(self)

        self.holidayManager = HolidayManagerAI()

        self.fishManager = FishManagerAI()

        self.petMgr = PetManagerAI.PetManagerAI(self)

        self.cogSuitMgr = CogSuitManagerAI.CogSuitManagerAI(self)
        self.promotionMgr = PromotionManagerAI.PromotionManagerAI(self)

        self.mintMgr = MintManagerAI.MintManagerAI(self)
        self.factoryMgr = FactoryManagerAI.FactoryManagerAI(self)
        self.lawOfficeMgr = LawOfficeManagerAI.LawOfficeManagerAI(self)
        self.countryClubMgr = CountryClubManagerAI.CountryClubManagerAI(self)

    def getTrackClsends(self):
        return False

    def handleConnected(self):
        self.districtId = self.allocateChannel()
        self.distributedDistrict = ToontownDistrictAI(self)
        self.distributedDistrict.setName(self.districtName)
        self.distributedDistrict.generateWithRequiredAndId(simbase.air.districtId,
                                                           self.getGameDoId(), 2)

        # Claim ownership of that district...
        dg = PyDatagram()
        dg.addServerHeader(simbase.air.districtId, simbase.air.ourChannel, STATESERVER_OBJECT_SET_AI)
        dg.addChannel(simbase.air.ourChannel)
        simbase.air.send(dg)

        self.createGlobals()
        self.createZones()

        self.distributedDistrict.b_setAvailable(1)
        self.notify.info('Done.')

    def incrementPopulation(self):
        self.districtStats.b_setAvatarCount(self.districtStats.getAvatarCount() + 1)

    def decrementPopulation(self):
        self.districtStats.b_setAvatarCount(self.districtStats.getAvatarCount() - 1)

    def allocateZone(self):
        return self.zoneAllocator.allocate()

    def deallocateZone(self, zone):
        self.zoneAllocator.free(zone)

    def getZoneDataStore(self):
        return self.zoneDataStore

    def getAvatarExitEvent(self, avId):
        return 'distObjDelete-%d' % avId

    def createGlobals(self):
        self.districtStats = ToontownDistrictStatsAI(self)
        self.districtStats.settoontownDistrictId(self.districtId)
        self.districtStats.generateWithRequiredAndId(self.allocateChannel(),
                                                     self.getGameDoId(), 3)

        self.timeManager = TimeManagerAI(self)
        self.timeManager.generateWithRequired(2)

        self.newsManager = NewsManagerAI(self)
        self.newsManager.generateWithRequired(2)

        self.magicWordManager = MagicWordManagerAI(self)
        self.magicWordManager.generateWithRequired(2)

        self.safeZoneManager = SafeZoneManagerAI(self)
        self.safeZoneManager.generateWithRequired(2)

        self.friendManager = FriendManagerAI(self)
        self.friendManager.generateWithRequired(2)

        self.partyManager = DistributedPartyManagerAI(self)
        self.partyManager.generateWithRequired(2)

        self.trophyMgr = DistributedTrophyMgrAI(self)
        self.trophyMgr.generateWithRequired(2)

        # setup our view of the global party manager ud
        self.globalPartyMgr = self.generateGlobalObject(OTP_DO_ID_GLOBAL_PARTY_MANAGER, 'GlobalPartyManager')

        self.estateManager = EstateManagerAI(self)
        self.estateManager.generateWithRequired(2)

    def createZones(self):
        self.hoods.append(TTHoodAI.TTHoodAI(self))
        self.hoods.append(DDHoodAI.DDHoodAI(self))
        self.hoods.append(DGHoodAI.DGHoodAI(self))
        self.hoods.append(BRHoodAI.BRHoodAI(self))
        self.hoods.append(MMHoodAI.MMHoodAI(self))
        self.hoods.append(DLHoodAI.DLHoodAI(self))
        self.hoods.append(GSHoodAI.GSHoodAI(self))
        self.hoods.append(OZHoodAI.OZHoodAI(self))
        self.hoods.append(GZHoodAI.GZHoodAI(self))
        self.hoods.append(SellbotHQAI.SellbotHQAI(self))
        self.hoods.append(CashbotHQAI.CashbotHQAI(self))
        self.hoods.append(LawbotHQAI.LawbotHQAI(self))
        self.hoods.append(BossbotHQAI.BossbotHQAI(self))

    def genDNAFileName(self, zoneId):
        zoneId = ZoneUtil.getCanonicalZoneId(zoneId)
        hoodId = ZoneUtil.getCanonicalHoodId(zoneId)
        hood = ToontownGlobals.dnaMap[hoodId]
        if hoodId == zoneId:
            zoneId = 'sz'
            phase = ToontownGlobals.phaseMap[hoodId]
        else:
            phase = ToontownGlobals.streetPhaseMap[hoodId]

        return 'phase_%s/dna/%s_%s.dna' % (phase, hood, zoneId)

    def loadDNAFileAI(self, dnastore, filename):
        return loadDNAFileAI(dnastore, filename)

    def trueUniqueName(self, name):
        return self.uniqueName(name)
