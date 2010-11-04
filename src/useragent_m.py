import re

class UserAgent:

    user_agent = ""
    carrier = None

    def setUserAgent(self, agent):
        self.user_agent = agent

        if(re.match("^DoCoMo", agent)):
            self.carrier = "DOCOMO"
        elif(re.match("^J-PHONE|^Vodafone|^SoftBank", agent)):
            self.carrier = "SOFTBANK"
        elif(re.match("^UP.Browser|^KDDI", agent)):
            self.carrier = "KDDI"
        else:
            self.carrier = None

    def getUserAgent(self):
        return self.user_agent

    def getCarrier(self):
        return self.carrier

    def isDocomo(self):
        return self.carrier == "DOCOMO"

    def isSoftBank(self):
        return self.carrier == "SOFTBANK"

    def isKDDI(self):
        return self.carrier == "KDDI"


