# -*- coding: utf-8 -*-

from datetime import datetime
import struct
import random
import copy
import os
import codecs

# fres(ext_opcode=0b00000110000)の処理入れるのめんどくさいから抜きで
fpop2 = [0b01000010000, 0b00000011100, 0b00000011110, 0b00010010000, 0b00100010000,
    0b00001010000, 0b00000011000, 0b00000110100, 0b00000101100]
fpop3 = [0b101010, 0b100100, 0b110010, 0b101000]
fpop4 = [0b111010, 0b111000, 0b111110, 0b111100, 0b101110]

ps2 = [0b01000010000, 0b00010010000, 0b00100010000, 0b00001010000, 0b00000110000, 0b00000110100]
ps3 = [0b00000101010, 0b00000101000, 0b00000100100, 0b10000100000, 0b10001100000, 0b10010100000, 0b10011100000]
ps3mul = [0b110010, 0b011000, 0b011010]
ps4 = [0b111010, 0b011100, 0b011110, 0b111000, 0b111110, 0b111100, 0b101110, 0b010100, 0b010110]

def int2hexstr(num):
    if 0x00000000 < num < 0xFFFFFFFF:
        # 参考にしました
        return hex(num).lstrip("0x").rstrip("L").zfill(8).upper()
    else:
        raise ValueError

class PPC_GenCenter:
    def __init__(self, rawmemf):
        with open(rawmemf, 'rb') as f:
            self.rawmem = f.read()
        self.start_addr = None
        self.end_addr = None
        self.codelst = []

    def get_gameid(self):
        return self.rawmem[:6]

    def set_memrange(self, start_addr, end_addr):
        # アドレスの入力は16進数で
        # 0xはあってもなくてもintが吸収してくれる
        bufints = map(lambda x: int(x, 16), [start_addr, end_addr])
        if not all(map(lambda x: 0 < x < 0x1800000, bufints)):
            # アドレスが正常な範囲でない場合
            raise ValueError('Invalid address')
        elif any(map(lambda x: x % 4, bufints)):
            # 4で割り切れなければならない
            raise ValueError('Addresses must be multiples of 4')
        elif bufints[0] > bufints[1]:
            # 開始アドレスは終了アドレスよりも前でなければならない
            raise ValueError('Start address must be smaller than end address')
        self.start_addr = bufints[0]
        self.end_addr = bufints[1]

    def generate(self, fp=True, bbacknop=True, bforthnop=True, vector=True, force_b=False, allowdiv=False, regenerate=False):

        if not (self.start_addr and self.end_addr):
            raise BaseException('Address is required')
        self.codelst = []

        for addr in xrange(self.start_addr, self.end_addr, 4):
            firstbyte = ord(self.rawmem[addr])
            # 浮動小数演算命令かチェック(先頭6ビットが111011なら単精度、111111なら倍精度)
            if fp and firstbyte & 0b11101100 == 0b11101100:
                code = struct.unpack('>L', self.rawmem[addr:addr+4])[0]

                # 浮動小数点数を格納するレジスタの番号を取得
                # どうせreg[0]使わないからNoneでもいいや
                # reg = [(code & 0x3E00000) >> 21, (code & 0x1F0000) >> 16, (code & 0xF800) >> 11, code & 0x7C0 >> 6]
                reg = [None, (code & 0x1F0000) >> 16, (code & 0xF800) >> 11, code & 0x7C0 >> 6]

                ext_opcode = code & 0b11111111111
                ext_op = ext_opcode & 0b111111
                newcode = None

                # 浮動小数演算命令をランダムに別のものに変える
                if ext_opcode in fpop2:
                    # 使われるレジスタの数が2つの場合
                    while 1:
                        new_ext_op = random.choice(fpop2)
                        # なぜかfsqrtがうまくいかないので除く
                        if new_ext_op not in [ext_opcode, 0b00000101100]:
                            # fsqrtはマイナスあるとNaNになってしまうから除く
                            # ついでにfrsqrteも
                            # allowdivという変数名は何だったのか
                            if new_ext_op not in [0b00000101100, 0b00000110100] or allowdiv:
                                break
                    # 全部倍精度に統一(手抜き)
                    newcode = 0xFC000000 + (code & 0x03FFF800) + new_ext_op
                elif ext_op in fpop3:
                    # 使われるレジスタの数が3つの場合
                    # 命令の数が少ないのでめんどくさいとか言ってられない
                    if ext_op == 0b110010:
                        # fmulは番号を指定しているビットの位置が異なるので
                        reg[3] = reg[2]
                    while 1:
                        new_ext_op = random.choice(fpop3)
                        if new_ext_op != ext_op:
                            # fdiv, fdivsは除く
                            if new_ext_op != 0b00000100100 or allowdiv:
                                break
                    # fmulの場合レジスタを指定している部分のビットが異なるので修正
                    newcode = (code & 0xFFFF0000) + (reg[2] << (11,6)[new_ext_op == 0b110010]) + new_ext_op
                elif ext_op in fpop4:
                    # 使われるレジスタの数が4つの場合
                    while 1:
                        new_ext_op = random.choice(fpop4)
                        if new_ext_op != ext_op:
                            break
                    # 全部倍精度に統一(手抜き)
                    newcode = 0xFC000000 + (code & 0x03FFFFC0) + new_ext_op
                # 新しいコードが得られたら
                if newcode:
                    self.codelst.append([addr, newcode])

            # 分岐命令かチェック
            elif (bbacknop or bforthnop or force_b) and (firstbyte & 0b11110100 == 0b01000000):
                # bとblは先頭6ビットが01001Xで条件分岐は010000
                newcode = None
                if (bbacknop and (firstbyte & 0b00000100)) or (bforthnop and not (firstbyte & 0b00000100)):
                    newcode = 0x60000000
                elif firstbyte & 0b11111100 == 0b01000000:
                    # 条件分岐
                    if bbacknop or bforthnop:
                        buflst = []
                        if (bbacknop and (firstbyte & 0b00000100)) or (bforthnop and not (firstbyte & 0b00000100)):
                            buflst.append(0x60000000)
                        if force_b and dest < 0x8000:
                            buflst.append(0x48000000 + dest)
                        if buflst:
                            newcode = random.choice(buflst)
                    elif force_b:
                        # 強制分岐のみ
                        dest = struct.unpack('>H', self.rawmem[addr+2:addr+4])[0]
                        # 戻る方向のやつを強制分岐すると無限ループになる未来しか見えないから
                        if dest < 0x8000:
                            newcode = 0x48000000 + dest
                # 新しいコードが得られたら
                if newcode:
                    self.codelst.append([addr, newcode])

            # ベクトル演算の命令(Paired singles)かチェック
            elif vector and firstbyte & 0b11111100 == 0b00010000:
                code = struct.unpack('>L', self.rawmem[addr:addr+4])[0]

                # どうせreg[0]使わないからNoneでもいいや
                # reg = [(code & 0x3E00000) >> 21, (code & 0x1F0000) >> 16, (code & 0xF800) >> 11, code & 0x7C0 >> 6]
                reg = [None, (code & 0x1F0000) >> 16, (code & 0xF800) >> 11, code & 0x7C0 >> 6]

                ext_opcode = code & 0b11111111111
                ext_op = ext_opcode & 0b111111
                newcode = None

                # ベクトル演算命令をランダムに別のものに変える
                if ext_opcode in ps2:
                    # 使われるレジスタの数が2つの場合
                    while 1:
                        new_ext_op = random.choice(ps2)
                        if new_ext_op != ext_opcode:
                            # ps_resはf0が使えないらしいのでその場合は別のにする
                            if new_ext_op != 0b00000110000 or (allowdiv and reg[0] and reg[2]):
                                # ps_resとps_rsqrteは割り算含む
                                if new_ext_op != 0b00000110100 or allowdiv:
                                    break

                    # 生成
                    newcode = (code & 0xFFFFF800) + new_ext_op
                elif ext_opcode in ps3 or ext_op in ps3mul:
                    # 使われるレジスタの数が3つの場合
                    # 命令の数が少ないのでめんどくさいとか言ってられない
                    if ext_op in ps3mul:
                        # fmulは番号を指定しているビットの位置が異なるので
                        reg[3] = reg[2]
                    while 1:
                        new_ext_op = random.choice(ps3 + ps3mul)
                        # ps_divは割り算含む
                        if new_ext_op not in [ext_opcode, ext_op, (None, 0b00000100100)[allowdiv]]:
                            break
                    # ps_mul, ps_muls0, ps_muls1の場合レジスタを指定している部分のビットが異なるので修正
                    newcode = (code & 0xFFE00000) + (reg[2] << (11,6)[new_ext_op in ps3mul]) + new_ext_op
                elif ext_op in ps4:
                    # 使われるレジスタの数が4つの場合
                    while 1:
                        new_ext_op = random.choice(ps4)
                        if new_ext_op != ext_op:
                            break
                    # 生成
                    newcode = 0x10000000 + (code & 0x03FFFFC0) + new_ext_op
                # 新しいコードが得られたら
                if newcode:
                    self.codelst.append([addr, newcode])


    def get_code(self, codenum=0, proc=lambda l: int2hexstr(0x80000000+l[0]) + ',' + int2hexstr(l[1])):
        # 出力するコードの数を決める 0>=なら全部とする
        buflst = []
        if codenum > 0:
            bufcodelst = copy.copy(self.codelst)
            random.shuffle(bufcodelst)
            sortflag = True
        else:
            bufcodelst = self.codelst
            codenum = len(bufcodelst)
            sortflag = False

        # 一定個数のコードを順番に並べる(全部指定してるときは無駄な作業かもしれないが全部乗せはフリーズするだろうから
        for c in sorted(bufcodelst[:codenum], key=lambda x: x[0]):
            # 使える形式にコードを加工する
            # デフォルトではcsv(しかしこれは使い道が思いつかない(多分使うことはない
            buflst.append(proc(c))

        return "\r\n".join(buflst)

    def get_arcode(self, codenum=0):
        return self.get_code(codenum=codenum, proc=lambda l: int2hexstr(0x04000000+l[0]) + ' ' + int2hexstr(l[1]))

    def get_dolphinpatch(self, codenum=0):
        return self.get_code(codenum=codenum, proc=lambda l: '0x' + int2hexstr(0x80000000+l[0]) + ':dword:0x' + int2hexstr(l[1]))


if __name__ == '__main__':
    # 適当
    import sys
    import os
    import argparse
    if len(sys.argv) < 4:
        sys.exit('Usage: ' + sys.argv[0] + ' ram.raw startaddr endaddr (codenum) (option)\n  option: +1=fp,+2=bbacknop,+4=bforthnop,+8=vector,+16=forceb,+32=allowdiv (default is 31)')

    os.chdir(os.path.dirname(os.path.abspath(sys.argv[1])))
    filename = os.path.splitext(os.path.basename(os.path.abspath(sys.argv[1])))[0]

    gc = PPC_GenCenter(sys.argv[1])
    gc.set_memrange(sys.argv[2], sys.argv[3])
    if len(sys.argv) > 4:
        codenum = int(sys.argv[4])
    else:
        codenum = 0
    if len(sys.argv) > 5:
        option = int(sys.argv[5])
    else:
        option = 31
    gc.generate(option & 1, option & 2, option & 4, option & 8, option & 16, option & 32)

    patchtxt = gc.get_dolphinpatch(codenum)
    now = datetime.now().strftime("%Y%m%d-%H%M%S")

    inipath = os.path.join(os.path.expanduser("~"), 'Documents', 'Dolphin Emulator', 'GameSettings', (gc.get_gameid() + '.ini'))
    inidata = []

    # iniファイルにコードを加えておく
    codename = u'$チートバグ_' + unicode(codenum) + u'_' + unicode(option) + u'_' + unicode(now) + '\n'

    igonreflag = False
    patchflag = False

    if not os.path.exists(inipath):
        with open(inipath, 'w') as f:
            pass
    with codecs.open(inipath, 'r', 'utf-8') as f:
        for line in f:
            if line[0] == u'[':
                if u'[OnFrame_Enabled]' in line:
                    inidata.extend([u'[OnFrame_Enabled]\n', codename])
                    ignoreflag = True
                elif u'[Onframe]' in line:
                    inidata.extend([u'[OnFrame]\n', codename, patchtxt])
                    patchflag = True
                    ignoreflag = False
                else:
                    ignoreflag = False
            if not ignoreflag:
               inidata.append(line)

    if not patchflag:
        inidata.extend([u'[OnFrame_Enabled]\n', codename, u'[OnFrame]\n', codename, patchtxt])

    with codecs.open(inipath, 'w', 'utf-8') as f:
        f.write(u''.join(inidata))

    with open(filename + '_' + str(codenum) + '_' + str(option) + '_' + now + '.txt', 'w') as f:
        f.write(patchtxt)
    print "Done!"

