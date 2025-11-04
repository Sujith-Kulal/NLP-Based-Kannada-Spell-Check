# how to run the code
# python3 tokenizer_for_indian_languages_on_files.py --input InputFolder --output OutputFolder --lang 0
# lang parameter is a 2-digit ISO 639-1 code for languages.
# for languages ['hi', 'or', 'mn', 'as', 'bn', 'pa'], purna biram as sentence end marker, lang = 0
# for Urdu, '۔' as sentence end marker, lang = 1
# for languages ['en', 'gu', 'mr', 'ml', 'kn', 'te', 'ta'], '.' as sentence end marker, lang = 2
# works at folder and file level
import re
import argparse
import os


# patterns for tokenization
token_specification = [
    ('datemonth',
     r'^(0?[1-9]|1[012])[-\/\.](0?[1-9]|[12][0-9]|3[01])[-\/\.](1|2)\d\d\d$'),
    ('monthdate',
     r'^(0?[1-9]|[12][0-9]|3[01])[-\/\.](0?[1-9]|1[012])[-\/\.](1|2)\d\d\d$'),
    ('yearmonth',
     r'^((1|2)\d\d\d)[-\/\.](0?[1-9]|1[012])[-\/\.](0?[1-9]|[12][0-9]|3[01])'),
    ('EMAIL1', r'([\w\.])+@(\w)+\.(com|org|co\.in)$'),
    ('url1', r'(www\.)([-a-z0-9]+\.)*([-a-z0-9]+.*)(\/[-a-z0-9]+)*/i'),
    ('url', r'/((?:https?\:\/\/|www\.)(?:[-a-z0-9]+\.)*[-a-z0-9]+.*)/i'),
    ('BRACKET', r'[\(\)\[\]\{\}]'),       # Brackets
    ('NUMBER', r'^(\d+)([,\.]\d+)*(\w)*'),  # Integer or decimal number
    ('ASSIGN', r'[~:]'),          # Assignment operator
    ('END', r'[;_]'),           # Statement terminator
    ('EQUAL', r'='),   # Equals
    ('OP', r'[+*\/\-]'),    # Arithmetic operators
    ('QUOTES', r'[\"\'‘’]'),          # quotes
    ('Fullstop', r'(\.+)$'),
    ('ellips', r'\.(\.)+'),
    ('HYPHEN', r'[-+\|+]'),
    ('Slashes', r'[\\\/]'),
    ('COMMA12', r'[,%]'),
    ('hin_stop', r'।'),
    ('quotes_question', r'[”\?]'),
    ('hashtag', r'#')
]
# compile regular expressions
tok_regex = '|'.join('(?P<%s>%s)' % pair for pair in token_specification)
get_token = re.compile(tok_regex)

words_with_dot=["ಡಾ.","ಚ.ಕಿ.ಮೀ.","ಕಿ.ಮೀ.","ಎಂ. ವಿ.","ಎಂ.","ಎಲ್.","ವಿ.","ಎಂ.ಎಲ್."," ಶ್ರೀಮತಿ.ಎಲ್.","ಸ.ನಂ.","ರೂ.","ನಂ.","ಕೆ.ಜಿ.","ಮೀ.","CPCL.","೧.","೨.","೩.","?","ಎಂ.ಆರ್.ಐ.","...","..","16.","1.2.3.4.5.6.7.8.9.10.11.12.13.14.15.16.17.18.19.20.21.22.23.24.25.26.27.28.29","i.","ii.","iii.","iv.","a.","b.","c.","d.","e.","f.","g.","h.","i.","j."];

def tokenize(list_s):
    """Tokenize a list of tokens."""
    tkns = []
    for wrds in list_s:
        wrds_len = len(wrds)
        initial_pos = 0
        end_pos = 0
       
        if wrds in words_with_dot:
            tkns.append(wrds)
            continue      	
        while initial_pos <= (wrds_len-1):
            mo = get_token.match(wrds, initial_pos)
            if mo is not None and len(mo.group(0)) == wrds_len:
                tkns.append(wrds)
                initial_pos = wrds_len
            else:
                match_out = get_token.search(wrds, initial_pos)
                if match_out is not None:
                    end_pos = match_out.end()
                    if match_out.lastgroup == "NUMBER":
                        aa = wrds[initial_pos:]

                        #print(f"wrds : {wrds} || aa : {aa}")
                    else:
                        aa = wrds[initial_pos:(end_pos - 1)]
                    if aa != '':
                        tkns.append(aa)
                    if match_out.lastgroup != "NUMBER":
                        tkns.append(match_out.group(0))
                    if match_out.lastgroup != "NUMBER":
                        initial_pos = end_pos
                    else:
                        initial_pos = wrds_len

                else:
                    tkns.append(wrds[initial_pos:])
                    initial_pos = wrds_len
    return tkns


def tokenize_sentence(text, lang='kn'):
    """Compatibility wrapper expected by EnhancedSpellChecker."""
    if isinstance(text, (list, tuple)):
        return tokenize(list(text))

    try:
        parts = str(text).split()
        return tokenize(parts)
    except Exception:
        return []


def read_file_and_tokenize(input_file, output_file, lang_type):
    """Read file and tokenize."""
    string_sentences = ''
    file_read = open(input_file, 'r', encoding='utf-8')
    text = file_read.read().strip().replace(u'0xff', '')
    if lang_type == 0:
        sentences = re.findall('.*?।|.*?\n', text + '\n', re.UNICODE)
        endMarkers = ['?', '।', '!', '|']
    elif lang_type == 1:
        sentences = re.findall('.*?\n', text + '\n', re.UNICODE)
        endMarkers = ['؟', '!', '|', '۔']
    else:
        sentences = re.findall('.*?\n', text + '\n', re.UNICODE)
        endMarkers = ['?', '.', '!', '|']
    count_sentence = 1
    for index, sentence in enumerate(sentences):
        if sentence.strip() != '':
            list_tokens = tokenize(sentence.split())
            end_sentence_markers = [index + 1 for index, token in enumerate(list_tokens) if token in [ '.', '۔', '؟', '।',  '|']]
            if len(end_sentence_markers) > 0:
                if end_sentence_markers[-1] != len(list_tokens):
                    end_sentence_markers += [len(list_tokens)]
                end_sentence_markers_with_sentence_end_positions = [0] + end_sentence_markers
                sentence_boundaries = list(zip(end_sentence_markers_with_sentence_end_positions, end_sentence_markers_with_sentence_end_positions[1:]))
                for start, end in sentence_boundaries:
                    individual_sentence = list_tokens[start: end]
                    string_sentences += '<Sentence id=\'' + \
                        str(count_sentence) + '\'>\n'
                    mapped_tokens = list(map(lambda token_index: str(
                        token_index[0] + 1) + '\t' + token_index[1].strip() + '\tunk', list(enumerate(individual_sentence))))
                    string_sentences += '\n'.join(mapped_tokens) + \
                        '\n</Sentence>\n\n'
                    count_sentence += 1
            else:
                string_sentences += '<Sentence id=\'' + \
                        str(count_sentence) + '\'>\n'
                mapped_tokens = list(map(lambda token_index: str(
                    token_index[0] + 1) + '\t' + token_index[1].strip() + '\tunk', list(enumerate(list_tokens))))
                string_sentences += '\n'.join(mapped_tokens) + \
                    '\n</Sentence>\n\n'
                count_sentence += 1
        write_data_to_file(output_file, string_sentences)


def write_data_to_file(output_file, data):
    """Write data to file."""
    with open(output_file, 'w', encoding='utf-8') as file_write:
        file_write.write(data + '\n')


def main():
    """Pass arguments and call functions here."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--input', dest='inp', help="enter the input file path")
    parser.add_argument(
        '--output', dest='out', help="enter the output file path")
    parser.add_argument(
        '--lang', dest='lang', help="enter the language: two digit ISO code")
    args = parser.parse_args()
    if os.path.isdir(args.inp) and not os.path.isdir(args.out):
        os.makedirs(args.out)
    if args.lang in ['hi', 'or', 'mn', 'as', 'bn', 'pa']:
        lang = 0
    elif args.lang == 'ur':
        lang = 1
    elif args.lang in ['en', 'gu', 'mr', 'ml', 'kn', 'te', 'ta']:
        lang = 2
    else:
        lang = 0
    if os.path.isdir(args.inp):
        for root, dirs, files in os.walk(args.inp):
            for fl in files:
                input_path = os.path.join(root, fl)
                output_path = os.path.join(args.out, fl)
                read_file_and_tokenize(input_path, output_path, lang)
    else:
        read_file_and_tokenize(args.inp, args.out, lang)


if __name__ == '__main__':
    main()

