from yargy2 import Parser, rule, or_
from yargy2.predicates import in_

NUM_MAP = {
    'один': '1', 
    'первый': '1', 
    'два': '2', 
    'две': '2', 
    'второй': '2', 
    'три': '3', 
    'третий': '3', 
    'четыре': '4', 
    'четвертый': '4', 
    'пять': '5', 
    'пятый': '5', 
    'шесть': '6', 
    'шестой': '6', 
    'семь': '7', 
    'седьмой': '7', 
    'восемь': '8', 
    'восьмой': '8', 
    'девять': '9',
    'девятый': '9',
    'десять': '10', 
    'десятый': '10',
    'одиннадцать': '11', 
    'одиннадцатый': '11',
    'двенадцать': '12', 
    'двенадцатый': '12',
    'тринадцать': '13', 
    'тринадцатый': '13',
    'четырнадцать': '14', 
    'четырнадцатый': '14',
    'пятнадцать': '15',
    'пятнадцатый': '15',
    'шестнадцать': '16',
    'шестнадцатый': '16',
    'семнадцать': '17',
    'семнадцатый': '17',
    'восемнадцать': '18',
    'восемнадцатый': '18',
    'девятнадцать': '19',
    'девятнадцатый': '19',
    'двадцать': '20', 
    'двадцатый': '20',
    'тридцать': '30', 
    'тридцатый': '30',
    'сорок': '40', 
    'сороковой': '40',
    'пятьдесят': '50',
    'пятидесятый': '50',
    'шестьдесят': '60', 
    'шестидесятый': '60',
    'семьдесят': '70', 
    'семидесятый': '70',
    'восемьдесят': '80',
    'восьмидесятый': '80',
    'девяносто': '90',
    'девяностый': '90',
    'сто': '100', 
    'сотый': '100',
    'двести': '200',
    'двухсотый': '200',
    'триста': '300', 
    'трехсотый': '300',
    'четыреста': '400',
    'четырехсотый': '400',
    'пятьсот': '500', 
    'пятисотый': '500',
    'шестьсот': '600', 
    'шестисотый': '600',
    'семьсот': '700', 
    'семисотый': '700',
    'восемьсот': '800', 
    'восьмисотый': '800',
    'девятьсот': '900',
    'девятисотый': '900',
    'тысяча': '1000', 
    'тысячный': '1000', 
    'двухтысячный': '2000',
    'трехтысячный': '3000',
    'четырехтысячный': '4000',
    'пятиftyсячный': '5000',
    'шеститысячный': '6000',
    'семитысячный': '7000',
    'восемитысячный': '8000',
    'девятитысячный': '9000'
}

MATCHING_WORDS = list(NUM_MAP.keys())
MATCHING_WORDS.append("плейлист")
MATCHING_WORDS.append("тысяча")
MATCHING_WORDS.append("тысяч")
MATCHING_WORDS.append("тысячи")

playlist_rule = rule(in_(MATCHING_WORDS))

playlist_parser = Parser(playlist_rule)


def check_playlist_phrase(text):
    matches = list(playlist_parser.findall(text.lower()))

    if not matches:
        raise ValueError("No matching words found in the text.")

    positive_words = [m.tokens[0].value for m in matches]

    if positive_words[0] != "плейлист":
        raise ValueError("The first word in the text is not 'плейлист'.")

    positive_words  = positive_words[1:] if len(positive_words) > 1 else []

    if not positive_words:
        raise ValueError("No valid numbers found after 'плейлист'.")

    if len(positive_words) == 1:
        first_number = NUM_MAP.get(positive_words[0], 0)
        return int(first_number)

    first_word = positive_words[0]
    second_word = positive_words[1]
    sum = 0

    if first_word == "тысяча":
        second_number = NUM_MAP.get(second_word, 0)
        sum = 1000 + int(second_number)
        if len(positive_words) == 2:
            return sum
        positive_words = positive_words[2:]

    if second_word.startswith("тысяч"):
        first_number = NUM_MAP.get(first_word, 0)
        sum = int(first_number) * 1000 if first_number else 0
        if len(positive_words) == 2:
            return sum
        positive_words = positive_words[2:]


    for word in positive_words:
        number = NUM_MAP.get(word, 0)
        sum += int(number)

    return sum

import unittest

request_prefix = "загрузи плейлист"

class TestCheckPlaylistPhrase(unittest.TestCase):

    def test_1(self):
        self.assertEqual(check_playlist_phrase(request_prefix + " один"), 1)
        self.assertEqual(check_playlist_phrase(request_prefix + " первый"), 1)

    def test_5(self):
        self.assertEqual(check_playlist_phrase(request_prefix + " пять"), 5)    
        self.assertEqual(check_playlist_phrase(request_prefix + " пятый"), 5)

    def test_10(self):
        self.assertEqual(check_playlist_phrase(request_prefix + " десять"), 10)
        self.assertEqual(check_playlist_phrase(request_prefix + " десятый"), 10)

    def test_15(self):
        self.assertEqual(check_playlist_phrase(request_prefix + " пятнадцать"), 15)
        self.assertEqual(check_playlist_phrase(request_prefix + " пятнадцатый"), 15)

    def test_50(self):
        self.assertEqual(check_playlist_phrase(request_prefix + " пятьдесят"), 50)
        self.assertEqual(check_playlist_phrase(request_prefix + " пятидесятый"), 50)

    def test_500(self):
        self.assertEqual(check_playlist_phrase(request_prefix + " пятьсот"), 500)   
        self.assertEqual(check_playlist_phrase(request_prefix + " пятисотый"), 500)

    def test_1000(self):
        self.assertEqual(check_playlist_phrase(request_prefix + " тысяча"), 1000)
        self.assertEqual(check_playlist_phrase(request_prefix + " тысячный"), 1000)

    def test_1001(self):
        self.assertEqual(check_playlist_phrase(request_prefix + " тысяча один"), 1001)
        self.assertEqual(check_playlist_phrase(request_prefix + " тысяча первый"), 1001)

    def test_1010(self):
        self.assertEqual(check_playlist_phrase(request_prefix + " тысяча десять"), 1010)
        self.assertEqual(check_playlist_phrase(request_prefix + " тысяча десятый"), 1010)

    def test_1015(self):
        self.assertEqual(check_playlist_phrase(request_prefix + " тысяча пятнадцать"), 1015)
        self.assertEqual(check_playlist_phrase(request_prefix + " тысяча пятнадцатый"), 1015)

    def test_1050(self):
        self.assertEqual(check_playlist_phrase(request_prefix + " тысяча пятьдесят"), 1050)
        self.assertEqual(check_playlist_phrase(request_prefix + " тысяча пятидесятый"), 1050)   

    def test_1500(self):
        self.assertEqual(check_playlist_phrase(request_prefix + " тысяча пятьсот"), 1500)
        self.assertEqual(check_playlist_phrase(request_prefix + " тысяча пятисотый"), 1500)

    def test_2000(self):
        self.assertEqual(check_playlist_phrase(request_prefix + " две тысячи"), 2000)
        self.assertEqual(check_playlist_phrase(request_prefix + " двухтысячный"), 2000)

    def test_2001(self):
        self.assertEqual(check_playlist_phrase(request_prefix + " две тысячи один"), 2001)
        self.assertEqual(check_playlist_phrase(request_prefix + " две тысячи первый"), 2001)

    def test_2020(self):
        self.assertEqual(check_playlist_phrase(request_prefix + " две тысячи двадцать"), 2020)
        self.assertEqual(check_playlist_phrase(request_prefix + " две тысячи двадцатый"), 2020)

    def test_2025(self):
        self.assertEqual(check_playlist_phrase(request_prefix + " две тысячи двадцать пять"), 2025)
        self.assertEqual(check_playlist_phrase(request_prefix + " две тысячи двадцать пятый"), 2025)

    def test_2050(self):
        self.assertEqual(check_playlist_phrase(request_prefix + " две тысячи пятьдесят"), 2050)
        self.assertEqual(check_playlist_phrase(request_prefix + " две тысячи пятидесятый"), 2050)

    def test_2500(self):
        self.assertEqual(check_playlist_phrase(request_prefix + " две тысячи пятьсот"), 2500)
        self.assertEqual(check_playlist_phrase(request_prefix + " две тысячи пятисотый"), 2500)

    def six_is_ok(self):
        self.assertEqual(check_playlist_phrase(request_prefix + " шесть"), 6)
        self.assertEqual(check_playlist_phrase(request_prefix + " шестой"), 6)

    def test_3456(self):
        self.assertEqual(check_playlist_phrase(request_prefix + " три тысячи четыреста пятьдесят шесть"), 3456)
        self.assertEqual(check_playlist_phrase(request_prefix + " три тысячи четыреста пятьдесят шестой"), 3456)

if __name__ == "__main__":
    unittest.main()
