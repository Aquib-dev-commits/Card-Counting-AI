class CardCounter:

    # ==================================================
    # HI-LO VALUES
    # ==================================================

    HI_LO_VALUES = {

        # +1
        "2": 1,
        "3": 1,
        "4": 1,
        "5": 1,
        "6": 1,

        # 0
        "7": 0,
        "8": 0,
        "9": 0,

        # -1
        "10": -1,
        "J": -1,
        "Q": -1,
        "K": -1,
        "A": -1,
    }


    def __init__(
        self,
        deck_size=52,
    ):

        self.deck_size = deck_size

        self.reset()


    # ==================================================
    # RESET
    # ==================================================

    def reset(self):

        # Exact card classes already counted.
        #
        # Example:
        # {"5S", "KD", "2H"}
        self.seen_cards = set()

        self.running_count = 0


    # ==================================================
    # EXTRACT RANK
    # ==================================================

    @staticmethod
    def get_rank(card):

        if not card:
            return None

        card = str(
            card
        ).upper().strip()

        # 10c, 10d, 10h, 10s
        if card.startswith("10"):
            return "10"

        # Ac, Ad, Ah, As
        if card.startswith("A"):
            return "A"

        # Jc, Jd, Jh, Js
        if card.startswith("J"):
            return "J"

        # Qc, Qd, Qh, Qs
        if card.startswith("Q"):
            return "Q"

        # Kc, Kd, Kh, Ks
        if card.startswith("K"):
            return "K"

        # 2c ... 9s
        first_character = card[0]

        if first_character in {
            "2",
            "3",
            "4",
            "5",
            "6",
            "7",
            "8",
            "9",
        }:
            return first_character

        return None


    # ==================================================
    # COUNT VALUE
    # ==================================================

    @classmethod
    def card_value(cls, card):

        rank = cls.get_rank(
            card
        )

        if rank is None:
            return 0

        return cls.HI_LO_VALUES.get(
            rank,
            0
        )


    # ==================================================
    # PROCESS TRACKED CARDS
    # ==================================================

    def update(
        self,
        detections,
    ):

        if not detections:
            return self.get_stats()


        for detection in detections:

            card = str(
                detection.get(
                    "card",
                    ""
                )
            ).upper().strip()


            if not card:
                continue


            # --------------------------------------------------
            # Ignore cards already counted.
            # --------------------------------------------------

            if card in self.seen_cards:
                continue


            # --------------------------------------------------
            # Make sure this is a valid 52-card class.
            # --------------------------------------------------

            value = self.card_value(
                card
            )


            if (
                value == 0
                and
                self.get_rank(card)
                not in {
                    "7",
                    "8",
                    "9",
                }
            ):
                continue


            # --------------------------------------------------
            # Count card exactly once.
            # --------------------------------------------------

            self.seen_cards.add(
                card
            )

            self.running_count += value


        return self.get_stats()


    # ==================================================
    # CARDS REMAINING
    # ==================================================

    def cards_remaining(self):

        return max(
            0,
            self.deck_size -
            len(self.seen_cards)
        )


    # ==================================================
    # DECKS REMAINING
    # ==================================================

    def decks_remaining(self):

        remaining = (
            self.cards_remaining()
        )

        return max(
            remaining / self.deck_size,
            1 / self.deck_size
        )


    # ==================================================
    # TRUE COUNT
    # ==================================================

    def true_count(self):

        decks = (
            self.decks_remaining()
        )

        if decks <= 0:
            return 0.0

        return (
            self.running_count /
            decks
        )


    # ==================================================
    # STATS
    # ==================================================

    def get_stats(self):

        return {

            "running_count":
                self.running_count,

            "cards_counted":
                len(self.seen_cards),

            "cards_remaining":
                self.cards_remaining(),

            "decks_remaining":
                round(
                    self.decks_remaining(),
                    2
                ),

            "true_count":
                round(
                    self.true_count(),
                    2
                ),

            "counted_cards":
                sorted(
                    self.seen_cards
                ),
        }