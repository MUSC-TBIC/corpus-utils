import re
import sys

def read_file(input_txt_dir, input_ann_dir, annotation_types, sentence_spliter):
    with open(input_txt_dir) as f:
        lines = f.read().split(sentence_spliter)
        begin_offset = 0
        end_offset = 0
        sent_lst = []
        for l_idx, l in enumerate(lines):
            lst = []
            for t_idx, t in enumerate(re.findall(r"[\w]+|[.,!?;/:-]", l)):
                token_dict = {}
                token_dict['string'] = t
                token_dict['begin_offset'] = begin_offset
                end_offset = begin_offset + len(t)
                token_dict['end_offset'] = end_offset
                begin_offset = end_offset + 1
                token_dict['word_index'] = t_idx
                token_dict['sent_index'] = l_idx + 1
                token_dict['file_name'] = input_txt_dir.split('/')[-1]
                token_dict['BIO_annotation'] = 'O'
                lst.append(token_dict)
            sent_lst.append(lst)

    return sent_lst

def write_file(sent_lst, file):
    with open(file, 'w') as f:
        for sent in sent_lst:
            for dict in sent:
                for k, v in dict.items():
                    f.write("{}\t".format(v))
                f.write('\n')
            f.write('\n')


if __name__ == '__main__':
    input_txt_dir = sys.argv[1]
    input_ann_dir = sys.argv[2]
    #[LabName, LabValue]
    annotation_types = sys.argv[3]
    output_dir = sys.argv[4]
    #'\n'
    sentence_splitter = sys.argv[5]

    sent_lst = read_file(input_txt_dir, input_ann_dir, annotation_types, sentence_splitter)
    write_file(sent_lst, output_dir)