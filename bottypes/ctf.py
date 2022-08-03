from typing import List

from pydantic import BaseModel

from bottypes.challenge import Challenge


class CTF(BaseModel):
    """
    An object representation of an ongoing CTF.
    """

    channel_id: str
    name: str
    long_name: str
    challenges: List[Challenge] = []
    cred_user = ""
    cred_pw = ""
    finished = False
    finished_on = 0

    def add_challenge(self, challenge):
        """
        Add a challenge object to the list of challenges belonging
        to this CTF.
        challenge : A challenge object
        """
        self.challenges.append(challenge)
