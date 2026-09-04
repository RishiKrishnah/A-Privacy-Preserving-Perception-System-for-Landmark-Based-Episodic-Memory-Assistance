# Architecture

```text
                         WEBCAM
                            |
                            v
                      YOLO-World
                            |
             +--------------+--------------+
             |              |              |
          PERSON       PERSONAL OBJECTS   LANDMARKS
             |              |              |
             +--------------+--------------+
                            |
                            v
                     TRACKED OBJECTS
                            |
                     +------+------+
                     |             |
                     v             v
               HAND TRACKING   LANDMARK HISTORY
                     |             |
                     +------+------+
                            |
                            v
                   TEMPORAL EVENT ENGINE
                            |
                 +----------+----------+
                 |          |          |
                PICK       MOVE      PLACE
                                      |
                                      v
                              CONFIDENCE FILTER
                                      |
                                      v
                               SEMANTIC DEDUP
                                      |
                                      v
                                    SQLite
                                      |
                                      v
                                 Edge API
```
