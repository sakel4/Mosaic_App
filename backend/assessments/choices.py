from django.db import models

class AssessmentType(models.TextChoices):
    ASSESSMENT = "assessment", "Assessment"
    EXCERCISE = "exercise", "Exercise"

class Kind(models.TextChoices):
    PHONEME_MANIPULATION = "phoneme_manipulation", "Phoneme Manipulation"
    LETTER_SOUND = "letter_sound", "Letter Sound"
    WORD_READING_SAMPLE = "word_reading_sample", "Word Reading Sample"
    VISUAL_RETRIEVAL_SPEED = "visual_retrieval_speed", "Visual Retrieval Speed"
    READING_FLUENCY = "reading_fluency", "Reading Fluency"
    SPELLING = "spelling", "Spelling"
    COMPREHENSION = "comprehension", "comprehension"
    WORKING_MEMORY = "working_memory", "working_memory"
    
class Skill(models.TextChoices):
    PHONOLOGICAL_AWARENESS = "phonological_awareness", "Phonological Awareness"
    LETTER_SOUND = "letter_sound", "Letter Sound"
    LETTER_SOUND_ASSOCIATION = "letter_sound_association", "Letter Sound Association"
    DECODING_AND_WORD_RECOGNITION = "decoding_and_word_recognition", "Decoding and Word Recognition"
    DECODING = "decoding", "Decoding"
    WORD_RECOGNITION = "word_recognition", "Word Recognition"
    NAMING_SPEED = "naming_speed", "Naming Speed"
    READING_FLUENCY = "reading_fluency", "Reading Fluency"
    SPELLING = "spelling", "Spelling"
    COMPREHENSION = "comprehension", "Comprehension"
    WORKING_MEMORY = "working_memory", "Working Memory"
    
class ResponseType(models.TextChoices):
    SINGLE_CHOICE_SET = "single_choice_set", "Single Choice Set"
    SPOKEN = "spoken", "Spoken"
    TYPED_TEXT = "typed_text", "Typed Text"
    SEQUENCE = "sequence", "Sequence"