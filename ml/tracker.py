from math import sqrt


class CardTracker:

    def __init__(
        self,
        iou_threshold=0.25,
        max_missed=5,
        smoothing_alpha=0.6,
    ):

        self.iou_threshold = iou_threshold
        self.max_missed = max_missed
        self.smoothing_alpha = smoothing_alpha

        self.next_track_id = 1
        self.tracks = {}


    # ==================================================
    # RESET
    # ==================================================

    def reset(self):

        self.next_track_id = 1
        self.tracks = {}


    # ==================================================
    # BASIC GEOMETRY
    # ==================================================

    @staticmethod
    def center(box):

        x1, y1, x2, y2 = box

        return (
            (x1 + x2) / 2.0,
            (y1 + y2) / 2.0,
        )


    @staticmethod
    def width(box):

        return max(
            1.0,
            box[2] - box[0]
        )


    @staticmethod
    def height(box):

        return max(
            1.0,
            box[3] - box[1]
        )


    @staticmethod
    def area(box):

        return (
            CardTracker.width(box) *
            CardTracker.height(box)
        )


    @staticmethod
    def diagonal(box):

        return sqrt(
            CardTracker.width(box) ** 2 +
            CardTracker.height(box) ** 2
        )


    # ==================================================
    # IOU
    # ==================================================

    @staticmethod
    def iou(box_a, box_b):

        ax1, ay1, ax2, ay2 = box_a
        bx1, by1, bx2, by2 = box_b

        ix1 = max(ax1, bx1)
        iy1 = max(ay1, by1)

        ix2 = min(ax2, bx2)
        iy2 = min(ay2, by2)

        iw = max(
            0,
            ix2 - ix1
        )

        ih = max(
            0,
            iy2 - iy1
        )

        intersection = iw * ih

        area_a = CardTracker.area(
            box_a
        )

        area_b = CardTracker.area(
            box_b
        )

        union = (
            area_a +
            area_b -
            intersection
        )

        if union <= 0:
            return 0.0

        return intersection / union


    # ==================================================
    # CENTER DISTANCE
    # ==================================================

    @staticmethod
    def center_distance(
        box_a,
        box_b,
    ):

        ax, ay = CardTracker.center(
            box_a
        )

        bx, by = CardTracker.center(
            box_b
        )

        return sqrt(
            (ax - bx) ** 2 +
            (ay - by) ** 2
        )


    # ==================================================
    # DUPLICATE SAME-CARD DETECTIONS
    #
    # A physical card can cause YOLO to detect the
    # same rank/suit at two opposite corners.
    #
    # Example:
    #
    #       5s
    #
    #       [small box]
    #
    #              ...
    #
    #                    [small box]
    #
    #       5s
    #
    # These must become ONE logical card.
    # ==================================================

    def should_merge_same_card(
        self,
        detection_a,
        detection_b,
    ):

        card_a = str(
            detection_a.get(
                "card",
                ""
            )
        ).upper()

        card_b = str(
            detection_b.get(
                "card",
                ""
            )
        ).upper()


        # Different classes can never be merged.
        if card_a != card_b:
            return False


        box_a = detection_a.get(
            "box"
        )

        box_b = detection_b.get(
            "box"
        )


        if not box_a or not box_b:
            return False


        # --------------------------------------------------
        # Rule 1: Significant overlap
        # --------------------------------------------------

        overlap = self.iou(
            box_a,
            box_b
        )

        if overlap >= 0.10:
            return True


        # --------------------------------------------------
        # Rule 2: Corner detections
        #
        # The YOLO boxes are often tiny because YOLO is
        # seeing the rank/suit marking rather than the
        # entire physical card.
        #
        # Therefore center distance must be evaluated
        # relative to the detection size.
        # --------------------------------------------------

        distance = self.center_distance(
            box_a,
            box_b
        )


        diag_a = self.diagonal(
            box_a
        )

        diag_b = self.diagonal(
            box_b
        )


        reference_size = max(
            diag_a,
            diag_b,
            1.0
        )


        # More generous than the previous 2.5×.
        #
        # This handles the case where the two corner
        # markings are farther apart because the card
        # is rotated or the camera moves.
        if distance <= (
            reference_size * 5.0
        ):

            return True


        # --------------------------------------------------
        # Rule 3: Very small YOLO boxes of the same card
        #
        # If both detections are small relative to the
        # frame and have the same class, they are very
        # likely two corner detections of one card.
        # --------------------------------------------------

        frame_width = (
            detection_a.get(
                "frame_width"
            )
            or
            detection_b.get(
                "frame_width"
            )
            or
            640
        )

        frame_height = (
            detection_a.get(
                "frame_height"
            )
            or
            detection_b.get(
                "frame_height"
            )
            or
            360
        )


        frame_area = (
            frame_width *
            frame_height
        )


        area_a_ratio = (
            self.area(box_a) /
            frame_area
        )

        area_b_ratio = (
            self.area(box_b) /
            frame_area
        )


        # Small marking-sized detections.
        if (
            area_a_ratio < 0.025
            and
            area_b_ratio < 0.025
            and
            distance <= (
                max(
                    frame_width,
                    frame_height
                ) * 0.35
            )
        ):

            return True


        return False


    # ==================================================
    # MERGE TWO DETECTIONS
    # ==================================================

    def merge_pair(
        self,
        detection_a,
        detection_b,
    ):

        boxes = [
            detection_a["box"],
            detection_b["box"],
        ]


        # Bounding rectangle covering both detections.
        x1 = min(
            box[0]
            for box in boxes
        )

        y1 = min(
            box[1]
            for box in boxes
        )

        x2 = max(
            box[2]
            for box in boxes
        )

        y2 = max(
            box[3]
            for box in boxes
        )


        # Keep the strongest detection as the base.
        if (
            float(
                detection_a.get(
                    "confidence",
                    0
                )
            )
            >=
            float(
                detection_b.get(
                    "confidence",
                    0
                )
            )
        ):

            merged = dict(
                detection_a
            )

        else:

            merged = dict(
                detection_b
            )


        merged["box"] = [
            int(x1),
            int(y1),
            int(x2),
            int(y2),
        ]


        merged["confidence"] = max(
            float(
                detection_a.get(
                    "confidence",
                    0
                )
            ),
            float(
                detection_b.get(
                    "confidence",
                    0
                )
            ),
        )


        merged["merged_detections"] = (
            int(
                detection_a.get(
                    "merged_detections",
                    1
                )
            )
            +
            int(
                detection_b.get(
                    "merged_detections",
                    1
                )
            )
        )


        return merged


    # ==================================================
    # MERGE ALL DUPLICATE DETECTIONS
    # ==================================================

    def merge_same_card_detections(
        self,
        detections,
    ):

        if not detections:
            return []


        # Work on copies so the original YOLO results
        # are not modified.
        remaining = [
            dict(detection)
            for detection in detections
        ]


        merged_results = []


        # --------------------------------------------------
        # Repeatedly search for mergeable pairs.
        #
        # This is better than a single pass because:
        #
        # A ↔ B
        # B ↔ C
        #
        # can all belong to the same physical card.
        # --------------------------------------------------

        changed = True


        while changed:

            changed = False

            result = []

            i = 0


            while i < len(remaining):

                current = remaining[i]

                merged_current = False

                j = i + 1


                while j < len(remaining):

                    candidate = remaining[j]


                    if self.should_merge_same_card(
                        current,
                        candidate,
                    ):

                        current = self.merge_pair(
                            current,
                            candidate
                        )


                        remaining.pop(j)

                        changed = True

                        merged_current = True

                        # Do not increment j because the
                        # list shifted.
                        continue


                    j += 1


                result.append(
                    current
                )

                i += 1


            remaining = result


        merged_results = remaining


        # --------------------------------------------------
        # IMPORTANT:
        # Always return a list.
        # --------------------------------------------------

        return merged_results


    # ==================================================
    # UPDATE TRACKER
    # ==================================================

    def update(
        self,
        detections,
    ):

        # --------------------------------------------------
        # STEP 1
        # Remove same-card duplicate detections.
        # --------------------------------------------------

        detections = (
            self.merge_same_card_detections(
                detections
            )
        )


        # ==================================================
        # NO DETECTIONS
        # ==================================================

        if not detections:

            for track_id in list(
                self.tracks.keys()
            ):

                self.tracks[
                    track_id
                ]["missed"] += 1


                if (
                    self.tracks[
                        track_id
                    ]["missed"]
                    >
                    self.max_missed
                ):

                    del self.tracks[
                        track_id
                    ]


            return [
                self._output_track(
                    track
                )
                for track in self.tracks.values()
            ]


        matched_tracks = set()
        matched_detections = set()


        # ==================================================
        # MATCH EXISTING TRACKS
        # ==================================================

        for track_id, track in list(
            self.tracks.items()
        ):

            best_index = None
            best_score = 0.0


            for index, detection in enumerate(
                detections
            ):

                if index in matched_detections:
                    continue


                track_card = str(
                    track.get(
                        "card",
                        ""
                    )
                ).upper()

                detection_card = str(
                    detection.get(
                        "card",
                        ""
                    )
                ).upper()


                # Never match different cards.
                if track_card != detection_card:
                    continue


                detection_box = detection.get(
                    "box"
                )


                if not detection_box:
                    continue


                current_iou = self.iou(
                    track["box"],
                    detection_box
                )


                # IoU is the primary score.
                score = current_iou


                # --------------------------------------------------
                # If IoU is low because the YOLO box represents
                # a small corner, use center proximity as fallback.
                # --------------------------------------------------

                distance = self.center_distance(
                    track["box"],
                    detection_box
                )


                reference_size = max(
                    self.diagonal(
                        track["box"]
                    ),
                    self.diagonal(
                        detection_box
                    ),
                    1.0
                )


                proximity_score = max(
                    0.0,
                    1.0 -
                    (
                        distance /
                        (
                            reference_size *
                            6.0
                        )
                    )
                )


                # Combine IoU and proximity.
                score = max(
                    current_iou,
                    proximity_score * 0.5
                )


                if score > best_score:

                    best_score = score

                    best_index = index


            # ==================================================
            # MATCH FOUND
            # ==================================================

            if (
                best_index is not None
                and
                best_score >= 0.25
            ):

                detection = detections[
                    best_index
                ]


                matched_tracks.add(
                    track_id
                )

                matched_detections.add(
                    best_index
                )


                old_box = track["box"]
                new_box = detection["box"]


                alpha = (
                    self.smoothing_alpha
                )


                # --------------------------------------------------
                # Temporal smoothing
                # --------------------------------------------------

                smoothed_box = [

                    int(
                        old_box[0] *
                        (1 - alpha)
                        +
                        new_box[0] *
                        alpha
                    ),

                    int(
                        old_box[1] *
                        (1 - alpha)
                        +
                        new_box[1] *
                        alpha
                    ),

                    int(
                        old_box[2] *
                        (1 - alpha)
                        +
                        new_box[2] *
                        alpha
                    ),

                    int(
                        old_box[3] *
                        (1 - alpha)
                        +
                        new_box[3] *
                        alpha
                    ),
                ]


                track["box"] = (
                    smoothed_box
                )


                # --------------------------------------------------
                # Smooth confidence
                # --------------------------------------------------

                old_confidence = float(
                    track.get(
                        "confidence",
                        0
                    )
                )

                new_confidence = float(
                    detection.get(
                        "confidence",
                        old_confidence
                    )
                )


                track["confidence"] = (
                    old_confidence *
                    (1 - alpha)
                    +
                    new_confidence *
                    alpha
                )


                track["missed"] = 0


                # --------------------------------------------------
                # Update metadata
                # --------------------------------------------------

                if "frame_width" in detection:

                    track["frame_width"] = (
                        detection["frame_width"]
                    )


                if "frame_height" in detection:

                    track["frame_height"] = (
                        detection["frame_height"]
                    )


        # ==================================================
        # CREATE NEW TRACKS
        # ==================================================

        for index, detection in enumerate(
            detections
        ):

            if index in matched_detections:
                continue


            box = detection.get(
                "box",
                [
                    0,
                    0,
                    0,
                    0,
                ]
            )


            track_id = (
                self.next_track_id
            )

            self.next_track_id += 1


            self.tracks[
                track_id
            ] = {

                "track_id":
                    track_id,

                "card":
                    detection.get(
                        "card",
                        "?"
                    ),

                "class_id":
                    detection.get(
                        "class_id"
                    ),

                "confidence":
                    float(
                        detection.get(
                            "confidence",
                            0
                        )
                    ),

                "box":
                    list(box),

                "frame_width":
                    detection.get(
                        "frame_width"
                    ),

                "frame_height":
                    detection.get(
                        "frame_height"
                    ),

                "missed":
                    0,
            }


        # ==================================================
        # REMOVE OLD TRACKS
        # ==================================================

        for track_id in list(
            self.tracks.keys()
        ):

            if track_id in matched_tracks:
                continue


            track = self.tracks[
                track_id
            ]


            # Newly created tracks already have missed=0.
            if track["missed"] == 0:
                continue


            track["missed"] += 1


            if (
                track["missed"]
                >
                self.max_missed
            ):

                del self.tracks[
                    track_id
                ]


        # ==================================================
        # RETURN TRACKS
        # ==================================================

        return [
            self._output_track(
                track
            )
            for track in self.tracks.values()
        ]


    # ==================================================
    # OUTPUT
    # ==================================================

    @staticmethod
    def _output_track(
        track
    ):

        return {

            "track_id":
                track["track_id"],

            "card":
                track["card"],

            "class_id":
                track.get(
                    "class_id"
                ),

            "confidence":
                float(
                    track["confidence"]
                ),

            "box":
                list(
                    track["box"]
                ),

            "frame_width":
                track.get(
                    "frame_width"
                ),

            "frame_height":
                track.get(
                    "frame_height"
                ),
        }