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
    'пятитысячный': '5000',
    'шеститысячный': '6000',
    'семитысячный': '7000',
    'восемитысячный': '8000',
    'девятитысячный': '9000'
}

MATCHING_WORDS = list(NUM_MAP.keys())
MATCHING_WORDS.append("плейлист")
MATCHING_WORDS.append("плэй")
MATCHING_WORDS.append("лист")
MATCHING_WORDS.append("тысяча")
MATCHING_WORDS.append("тысяч")
MATCHING_WORDS.append("тысячи")

playlist_rule = rule(in_(MATCHING_WORDS))

playlist_parser = Parser(playlist_rule)


def check_playlist_phrase(text):
    matches = list(playlist_parser.findall(text.lower()))

    if not matches:
        return 0

    positive_words = [m.tokens[0].value for m in matches]
    if not positive_words or  len(positive_words) < 2:
        return 0

    first_word = positive_words[0]
    second_word = positive_words[1] if len(positive_words) > 1 else ''

    if first_word == "плейлист":
        positive_words  = positive_words[1:] if len(positive_words) > 1 else []

    if first_word == "плэй" and second_word == "лист":
        positive_words  = positive_words[2:] if len(positive_words) > 2 else []

    if not positive_words:
        return 0

    first_word = positive_words[0]

    if len(positive_words) == 1:
        first_number = NUM_MAP.get(positive_words[0], 0)
        return int(first_number)

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

request_prefix_1 = "загрузи плейлист"
request_prefix_2 = "загрузи плэй лист"

class TestCheckPlaylistPhrase(unittest.TestCase):

    def test_1(self):
        self.assertEqual(check_playlist_phrase(request_prefix_1 + " один"), 1)
        self.assertEqual(check_playlist_phrase(request_prefix_1 + " первый"), 1)
        self.assertEqual(check_playlist_phrase(request_prefix_2 + " один"), 1)
        self.assertEqual(check_playlist_phrase(request_prefix_2 + " первый"), 1)
    def test_5(self):
        self.assertEqual(check_playlist_phrase(request_prefix_1 + " пять"), 5)    
        self.assertEqual(check_playlist_phrase(request_prefix_1 + " пятый"), 5)
        self.assertEqual(check_playlist_phrase(request_prefix_2 + " пять"), 5)    
        self.assertEqual(check_playlist_phrase(request_prefix_2 + " пятый"), 5)

    def test_10(self):
        self.assertEqual(check_playlist_phrase(request_prefix_1 + " десять"), 10)
        self.assertEqual(check_playlist_phrase(request_prefix_1 + " десятый"), 10)
        self.assertEqual(check_playlist_phrase(request_prefix_2 + " десять"), 10)
        self.assertEqual(check_playlist_phrase(request_prefix_2 + " десятый"), 10)

    def test_15(self):
        self.assertEqual(check_playlist_phrase(request_prefix_1 + " пятнадцать"), 15)
        self.assertEqual(check_playlist_phrase(request_prefix_1 + " пятнадцатый"), 15)
        self.assertEqual(check_playlist_phrase(request_prefix_2 + " пятнадцать"), 15)
        self.assertEqual(check_playlist_phrase(request_prefix_2 + " пятнадцатый"), 15)

    def test_50(self):
        self.assertEqual(check_playlist_phrase(request_prefix_1 + " пятьдесят"), 50)
        self.assertEqual(check_playlist_phrase(request_prefix_1 + " пятидесятый"), 50)
        self.assertEqual(check_playlist_phrase(request_prefix_2 + " пятьдесят"), 50)
        self.assertEqual(check_playlist_phrase(request_prefix_2 + " пятидесятый"), 50)

    def test_500(self):
        self.assertEqual(check_playlist_phrase(request_prefix_1 + " пятьсот"), 500)   
        self.assertEqual(check_playlist_phrase(request_prefix_1 + " пятисотый"), 500)
        self.assertEqual(check_playlist_phrase(request_prefix_2 + " пятьсот"), 500)   
        self.assertEqual(check_playlist_phrase(request_prefix_2 + " пятисотый"), 500)

    def test_1000(self):
        self.assertEqual(check_playlist_phrase(request_prefix_1 + " тысяча"), 1000)
        self.assertEqual(check_playlist_phrase(request_prefix_1 + " тысячный"), 1000)
        self.assertEqual(check_playlist_phrase(request_prefix_2 + " тысяча"), 1000)
        self.assertEqual(check_playlist_phrase(request_prefix_2 + " тысячный"), 1000)

    def test_1001(self):
        self.assertEqual(check_playlist_phrase(request_prefix_1 + " тысяча один"), 1001)
        self.assertEqual(check_playlist_phrase(request_prefix_1 + " тысяча первый"), 1001)
        self.assertEqual(check_playlist_phrase(request_prefix_2 + " тысяча один"), 1001)
        self.assertEqual(check_playlist_phrase(request_prefix_2 + " тысяча первый"), 1001)

    def test_1010(self):
        self.assertEqual(check_playlist_phrase(request_prefix_1 + " тысяча десять"), 1010)
        self.assertEqual(check_playlist_phrase(request_prefix_1 + " тысяча десятый"), 1010)
        self.assertEqual(check_playlist_phrase(request_prefix_2 + " тысяча десять"), 1010)
        self.assertEqual(check_playlist_phrase(request_prefix_2 + " тысяча десятый"), 1010)

    def test_1015(self):
        self.assertEqual(check_playlist_phrase(request_prefix_1 + " тысяча пятнадцать"), 1015)
        self.assertEqual(check_playlist_phrase(request_prefix_1 + " тысяча пятнадцатый"), 1015)
        self.assertEqual(check_playlist_phrase(request_prefix_2 + " тысяча пятнадцать"), 1015)
        self.assertEqual(check_playlist_phrase(request_prefix_2 + " тысяча пятнадцатый"), 1015)

    def test_1050(self):
        self.assertEqual(check_playlist_phrase(request_prefix_1 + " тысяча пятьдесят"), 1050)
        self.assertEqual(check_playlist_phrase(request_prefix_1 + " тысяча пятидесятый"), 1050)   
        self.assertEqual(check_playlist_phrase(request_prefix_2 + " тысяча пятьдесят"), 1050)
        self.assertEqual(check_playlist_phrase(request_prefix_2 + " тысяча пятидесятый"), 1050)   

    def test_1500(self):
        self.assertEqual(check_playlist_phrase(request_prefix_1 + " тысяча пятьсот"), 1500)
        self.assertEqual(check_playlist_phrase(request_prefix_1 + " тысяча пятисотый"), 1500)
        self.assertEqual(check_playlist_phrase(request_prefix_2 + " тысяча пятьсот"), 1500)
        self.assertEqual(check_playlist_phrase(request_prefix_2 + " тысяча пятисотый"), 1500)

    def test_2000(self):
        self.assertEqual(check_playlist_phrase(request_prefix_1 + " две тысячи"), 2000)
        self.assertEqual(check_playlist_phrase(request_prefix_1 + " двухтысячный"), 2000)
        self.assertEqual(check_playlist_phrase(request_prefix_2 + " две тысячи"), 2000)
        self.assertEqual(check_playlist_phrase(request_prefix_2 + " двухтысячный"), 2000)

    def test_2001(self):
        self.assertEqual(check_playlist_phrase(request_prefix_1 + " две тысячи один"), 2001)
        self.assertEqual(check_playlist_phrase(request_prefix_1 + " две тысячи первый"), 2001)
        self.assertEqual(check_playlist_phrase(request_prefix_2 + " две тысячи один"), 2001)
        self.assertEqual(check_playlist_phrase(request_prefix_2 + " две тысячи первый"), 2001)

    def test_2020(self):
        self.assertEqual(check_playlist_phrase(request_prefix_1 + " две тысячи двадцать"), 2020)
        self.assertEqual(check_playlist_phrase(request_prefix_1 + " две тысячи двадцатый"), 2020)
        self.assertEqual(check_playlist_phrase(request_prefix_2 + " две тысячи двадцать"), 2020)
        self.assertEqual(check_playlist_phrase(request_prefix_2 + " две тысячи двадцатый"), 2020)

    def test_2025(self):
        self.assertEqual(check_playlist_phrase(request_prefix_1 + " две тысячи двадцать пять"), 2025)
        self.assertEqual(check_playlist_phrase(request_prefix_1 + " две тысячи двадцать пятый"), 2025)
        self.assertEqual(check_playlist_phrase(request_prefix_2 + " две тысячи двадцать пять"), 2025)
        self.assertEqual(check_playlist_phrase(request_prefix_2 + " две тысячи двадцать пятый"), 2025)

    def test_2050(self):
        self.assertEqual(check_playlist_phrase(request_prefix_1 + " две тысячи пятьдесят"), 2050)
        self.assertEqual(check_playlist_phrase(request_prefix_1 + " две тысячи пятидесятый"), 2050)
        self.assertEqual(check_playlist_phrase(request_prefix_1 + " две тысячи пятьдесят"), 2050)
        self.assertEqual(check_playlist_phrase(request_prefix_1 + " две тысячи пятидесятый"), 2050)

    def test_2500(self):
        self.assertEqual(check_playlist_phrase(request_prefix_1 + " две тысячи пятьсот"), 2500)
        self.assertEqual(check_playlist_phrase(request_prefix_1 + " две тысячи пятисотый"), 2500)
        self.assertEqual(check_playlist_phrase(request_prefix_1 + " две тысячи пятьсот"), 2500)
        self.assertEqual(check_playlist_phrase(request_prefix_1 + " две тысячи пятисотый"), 2500)

    def six_is_ok(self):
        self.assertEqual(check_playlist_phrase(request_prefix_1 + " шесть"), 6)
        self.assertEqual(check_playlist_phrase(request_prefix_1 + " шестой"), 6)
        self.assertEqual(check_playlist_phrase(request_prefix_2 + " шесть"), 6)
        self.assertEqual(check_playlist_phrase(request_prefix_2 + " шестой"), 6)

    def test_3456(self):
        self.assertEqual(check_playlist_phrase(request_prefix_1 + " три тысячи четыреста пятьдесят шесть"), 3456)
        self.assertEqual(check_playlist_phrase(request_prefix_1 + " три тысячи четыреста пятьдесят шестой"), 3456)
        self.assertEqual(check_playlist_phrase(request_prefix_2 + " три тысячи четыреста пятьдесят шесть"), 3456)
        self.assertEqual(check_playlist_phrase(request_prefix_2 + " три тысячи четыреста пятьдесят шестой"), 3456)

if __name__ == "__main__":
    unittest.main()
