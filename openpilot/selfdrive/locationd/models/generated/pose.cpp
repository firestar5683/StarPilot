#include "pose.h"

namespace {
#define DIM 18
#define EDIM 18
#define MEDIM 18
typedef void (*Hfun)(double *, double *, double *);
const static double MAHA_THRESH_4 = 7.814727903251177;
const static double MAHA_THRESH_10 = 7.814727903251177;
const static double MAHA_THRESH_13 = 7.814727903251177;
const static double MAHA_THRESH_14 = 7.814727903251177;

/******************************************************************************
 *                      Code generated with SymPy 1.14.0                      *
 *                                                                            *
 *              See http://www.sympy.org/ for more information.               *
 *                                                                            *
 *                         This file is part of 'ekf'                         *
 ******************************************************************************/
void err_fun(double *nom_x, double *delta_x, double *out_5635938807142857948) {
   out_5635938807142857948[0] = delta_x[0] + nom_x[0];
   out_5635938807142857948[1] = delta_x[1] + nom_x[1];
   out_5635938807142857948[2] = delta_x[2] + nom_x[2];
   out_5635938807142857948[3] = delta_x[3] + nom_x[3];
   out_5635938807142857948[4] = delta_x[4] + nom_x[4];
   out_5635938807142857948[5] = delta_x[5] + nom_x[5];
   out_5635938807142857948[6] = delta_x[6] + nom_x[6];
   out_5635938807142857948[7] = delta_x[7] + nom_x[7];
   out_5635938807142857948[8] = delta_x[8] + nom_x[8];
   out_5635938807142857948[9] = delta_x[9] + nom_x[9];
   out_5635938807142857948[10] = delta_x[10] + nom_x[10];
   out_5635938807142857948[11] = delta_x[11] + nom_x[11];
   out_5635938807142857948[12] = delta_x[12] + nom_x[12];
   out_5635938807142857948[13] = delta_x[13] + nom_x[13];
   out_5635938807142857948[14] = delta_x[14] + nom_x[14];
   out_5635938807142857948[15] = delta_x[15] + nom_x[15];
   out_5635938807142857948[16] = delta_x[16] + nom_x[16];
   out_5635938807142857948[17] = delta_x[17] + nom_x[17];
}
void inv_err_fun(double *nom_x, double *true_x, double *out_4989912554372507650) {
   out_4989912554372507650[0] = -nom_x[0] + true_x[0];
   out_4989912554372507650[1] = -nom_x[1] + true_x[1];
   out_4989912554372507650[2] = -nom_x[2] + true_x[2];
   out_4989912554372507650[3] = -nom_x[3] + true_x[3];
   out_4989912554372507650[4] = -nom_x[4] + true_x[4];
   out_4989912554372507650[5] = -nom_x[5] + true_x[5];
   out_4989912554372507650[6] = -nom_x[6] + true_x[6];
   out_4989912554372507650[7] = -nom_x[7] + true_x[7];
   out_4989912554372507650[8] = -nom_x[8] + true_x[8];
   out_4989912554372507650[9] = -nom_x[9] + true_x[9];
   out_4989912554372507650[10] = -nom_x[10] + true_x[10];
   out_4989912554372507650[11] = -nom_x[11] + true_x[11];
   out_4989912554372507650[12] = -nom_x[12] + true_x[12];
   out_4989912554372507650[13] = -nom_x[13] + true_x[13];
   out_4989912554372507650[14] = -nom_x[14] + true_x[14];
   out_4989912554372507650[15] = -nom_x[15] + true_x[15];
   out_4989912554372507650[16] = -nom_x[16] + true_x[16];
   out_4989912554372507650[17] = -nom_x[17] + true_x[17];
}
void H_mod_fun(double *state, double *out_1119877989261778800) {
   out_1119877989261778800[0] = 1.0;
   out_1119877989261778800[1] = 0.0;
   out_1119877989261778800[2] = 0.0;
   out_1119877989261778800[3] = 0.0;
   out_1119877989261778800[4] = 0.0;
   out_1119877989261778800[5] = 0.0;
   out_1119877989261778800[6] = 0.0;
   out_1119877989261778800[7] = 0.0;
   out_1119877989261778800[8] = 0.0;
   out_1119877989261778800[9] = 0.0;
   out_1119877989261778800[10] = 0.0;
   out_1119877989261778800[11] = 0.0;
   out_1119877989261778800[12] = 0.0;
   out_1119877989261778800[13] = 0.0;
   out_1119877989261778800[14] = 0.0;
   out_1119877989261778800[15] = 0.0;
   out_1119877989261778800[16] = 0.0;
   out_1119877989261778800[17] = 0.0;
   out_1119877989261778800[18] = 0.0;
   out_1119877989261778800[19] = 1.0;
   out_1119877989261778800[20] = 0.0;
   out_1119877989261778800[21] = 0.0;
   out_1119877989261778800[22] = 0.0;
   out_1119877989261778800[23] = 0.0;
   out_1119877989261778800[24] = 0.0;
   out_1119877989261778800[25] = 0.0;
   out_1119877989261778800[26] = 0.0;
   out_1119877989261778800[27] = 0.0;
   out_1119877989261778800[28] = 0.0;
   out_1119877989261778800[29] = 0.0;
   out_1119877989261778800[30] = 0.0;
   out_1119877989261778800[31] = 0.0;
   out_1119877989261778800[32] = 0.0;
   out_1119877989261778800[33] = 0.0;
   out_1119877989261778800[34] = 0.0;
   out_1119877989261778800[35] = 0.0;
   out_1119877989261778800[36] = 0.0;
   out_1119877989261778800[37] = 0.0;
   out_1119877989261778800[38] = 1.0;
   out_1119877989261778800[39] = 0.0;
   out_1119877989261778800[40] = 0.0;
   out_1119877989261778800[41] = 0.0;
   out_1119877989261778800[42] = 0.0;
   out_1119877989261778800[43] = 0.0;
   out_1119877989261778800[44] = 0.0;
   out_1119877989261778800[45] = 0.0;
   out_1119877989261778800[46] = 0.0;
   out_1119877989261778800[47] = 0.0;
   out_1119877989261778800[48] = 0.0;
   out_1119877989261778800[49] = 0.0;
   out_1119877989261778800[50] = 0.0;
   out_1119877989261778800[51] = 0.0;
   out_1119877989261778800[52] = 0.0;
   out_1119877989261778800[53] = 0.0;
   out_1119877989261778800[54] = 0.0;
   out_1119877989261778800[55] = 0.0;
   out_1119877989261778800[56] = 0.0;
   out_1119877989261778800[57] = 1.0;
   out_1119877989261778800[58] = 0.0;
   out_1119877989261778800[59] = 0.0;
   out_1119877989261778800[60] = 0.0;
   out_1119877989261778800[61] = 0.0;
   out_1119877989261778800[62] = 0.0;
   out_1119877989261778800[63] = 0.0;
   out_1119877989261778800[64] = 0.0;
   out_1119877989261778800[65] = 0.0;
   out_1119877989261778800[66] = 0.0;
   out_1119877989261778800[67] = 0.0;
   out_1119877989261778800[68] = 0.0;
   out_1119877989261778800[69] = 0.0;
   out_1119877989261778800[70] = 0.0;
   out_1119877989261778800[71] = 0.0;
   out_1119877989261778800[72] = 0.0;
   out_1119877989261778800[73] = 0.0;
   out_1119877989261778800[74] = 0.0;
   out_1119877989261778800[75] = 0.0;
   out_1119877989261778800[76] = 1.0;
   out_1119877989261778800[77] = 0.0;
   out_1119877989261778800[78] = 0.0;
   out_1119877989261778800[79] = 0.0;
   out_1119877989261778800[80] = 0.0;
   out_1119877989261778800[81] = 0.0;
   out_1119877989261778800[82] = 0.0;
   out_1119877989261778800[83] = 0.0;
   out_1119877989261778800[84] = 0.0;
   out_1119877989261778800[85] = 0.0;
   out_1119877989261778800[86] = 0.0;
   out_1119877989261778800[87] = 0.0;
   out_1119877989261778800[88] = 0.0;
   out_1119877989261778800[89] = 0.0;
   out_1119877989261778800[90] = 0.0;
   out_1119877989261778800[91] = 0.0;
   out_1119877989261778800[92] = 0.0;
   out_1119877989261778800[93] = 0.0;
   out_1119877989261778800[94] = 0.0;
   out_1119877989261778800[95] = 1.0;
   out_1119877989261778800[96] = 0.0;
   out_1119877989261778800[97] = 0.0;
   out_1119877989261778800[98] = 0.0;
   out_1119877989261778800[99] = 0.0;
   out_1119877989261778800[100] = 0.0;
   out_1119877989261778800[101] = 0.0;
   out_1119877989261778800[102] = 0.0;
   out_1119877989261778800[103] = 0.0;
   out_1119877989261778800[104] = 0.0;
   out_1119877989261778800[105] = 0.0;
   out_1119877989261778800[106] = 0.0;
   out_1119877989261778800[107] = 0.0;
   out_1119877989261778800[108] = 0.0;
   out_1119877989261778800[109] = 0.0;
   out_1119877989261778800[110] = 0.0;
   out_1119877989261778800[111] = 0.0;
   out_1119877989261778800[112] = 0.0;
   out_1119877989261778800[113] = 0.0;
   out_1119877989261778800[114] = 1.0;
   out_1119877989261778800[115] = 0.0;
   out_1119877989261778800[116] = 0.0;
   out_1119877989261778800[117] = 0.0;
   out_1119877989261778800[118] = 0.0;
   out_1119877989261778800[119] = 0.0;
   out_1119877989261778800[120] = 0.0;
   out_1119877989261778800[121] = 0.0;
   out_1119877989261778800[122] = 0.0;
   out_1119877989261778800[123] = 0.0;
   out_1119877989261778800[124] = 0.0;
   out_1119877989261778800[125] = 0.0;
   out_1119877989261778800[126] = 0.0;
   out_1119877989261778800[127] = 0.0;
   out_1119877989261778800[128] = 0.0;
   out_1119877989261778800[129] = 0.0;
   out_1119877989261778800[130] = 0.0;
   out_1119877989261778800[131] = 0.0;
   out_1119877989261778800[132] = 0.0;
   out_1119877989261778800[133] = 1.0;
   out_1119877989261778800[134] = 0.0;
   out_1119877989261778800[135] = 0.0;
   out_1119877989261778800[136] = 0.0;
   out_1119877989261778800[137] = 0.0;
   out_1119877989261778800[138] = 0.0;
   out_1119877989261778800[139] = 0.0;
   out_1119877989261778800[140] = 0.0;
   out_1119877989261778800[141] = 0.0;
   out_1119877989261778800[142] = 0.0;
   out_1119877989261778800[143] = 0.0;
   out_1119877989261778800[144] = 0.0;
   out_1119877989261778800[145] = 0.0;
   out_1119877989261778800[146] = 0.0;
   out_1119877989261778800[147] = 0.0;
   out_1119877989261778800[148] = 0.0;
   out_1119877989261778800[149] = 0.0;
   out_1119877989261778800[150] = 0.0;
   out_1119877989261778800[151] = 0.0;
   out_1119877989261778800[152] = 1.0;
   out_1119877989261778800[153] = 0.0;
   out_1119877989261778800[154] = 0.0;
   out_1119877989261778800[155] = 0.0;
   out_1119877989261778800[156] = 0.0;
   out_1119877989261778800[157] = 0.0;
   out_1119877989261778800[158] = 0.0;
   out_1119877989261778800[159] = 0.0;
   out_1119877989261778800[160] = 0.0;
   out_1119877989261778800[161] = 0.0;
   out_1119877989261778800[162] = 0.0;
   out_1119877989261778800[163] = 0.0;
   out_1119877989261778800[164] = 0.0;
   out_1119877989261778800[165] = 0.0;
   out_1119877989261778800[166] = 0.0;
   out_1119877989261778800[167] = 0.0;
   out_1119877989261778800[168] = 0.0;
   out_1119877989261778800[169] = 0.0;
   out_1119877989261778800[170] = 0.0;
   out_1119877989261778800[171] = 1.0;
   out_1119877989261778800[172] = 0.0;
   out_1119877989261778800[173] = 0.0;
   out_1119877989261778800[174] = 0.0;
   out_1119877989261778800[175] = 0.0;
   out_1119877989261778800[176] = 0.0;
   out_1119877989261778800[177] = 0.0;
   out_1119877989261778800[178] = 0.0;
   out_1119877989261778800[179] = 0.0;
   out_1119877989261778800[180] = 0.0;
   out_1119877989261778800[181] = 0.0;
   out_1119877989261778800[182] = 0.0;
   out_1119877989261778800[183] = 0.0;
   out_1119877989261778800[184] = 0.0;
   out_1119877989261778800[185] = 0.0;
   out_1119877989261778800[186] = 0.0;
   out_1119877989261778800[187] = 0.0;
   out_1119877989261778800[188] = 0.0;
   out_1119877989261778800[189] = 0.0;
   out_1119877989261778800[190] = 1.0;
   out_1119877989261778800[191] = 0.0;
   out_1119877989261778800[192] = 0.0;
   out_1119877989261778800[193] = 0.0;
   out_1119877989261778800[194] = 0.0;
   out_1119877989261778800[195] = 0.0;
   out_1119877989261778800[196] = 0.0;
   out_1119877989261778800[197] = 0.0;
   out_1119877989261778800[198] = 0.0;
   out_1119877989261778800[199] = 0.0;
   out_1119877989261778800[200] = 0.0;
   out_1119877989261778800[201] = 0.0;
   out_1119877989261778800[202] = 0.0;
   out_1119877989261778800[203] = 0.0;
   out_1119877989261778800[204] = 0.0;
   out_1119877989261778800[205] = 0.0;
   out_1119877989261778800[206] = 0.0;
   out_1119877989261778800[207] = 0.0;
   out_1119877989261778800[208] = 0.0;
   out_1119877989261778800[209] = 1.0;
   out_1119877989261778800[210] = 0.0;
   out_1119877989261778800[211] = 0.0;
   out_1119877989261778800[212] = 0.0;
   out_1119877989261778800[213] = 0.0;
   out_1119877989261778800[214] = 0.0;
   out_1119877989261778800[215] = 0.0;
   out_1119877989261778800[216] = 0.0;
   out_1119877989261778800[217] = 0.0;
   out_1119877989261778800[218] = 0.0;
   out_1119877989261778800[219] = 0.0;
   out_1119877989261778800[220] = 0.0;
   out_1119877989261778800[221] = 0.0;
   out_1119877989261778800[222] = 0.0;
   out_1119877989261778800[223] = 0.0;
   out_1119877989261778800[224] = 0.0;
   out_1119877989261778800[225] = 0.0;
   out_1119877989261778800[226] = 0.0;
   out_1119877989261778800[227] = 0.0;
   out_1119877989261778800[228] = 1.0;
   out_1119877989261778800[229] = 0.0;
   out_1119877989261778800[230] = 0.0;
   out_1119877989261778800[231] = 0.0;
   out_1119877989261778800[232] = 0.0;
   out_1119877989261778800[233] = 0.0;
   out_1119877989261778800[234] = 0.0;
   out_1119877989261778800[235] = 0.0;
   out_1119877989261778800[236] = 0.0;
   out_1119877989261778800[237] = 0.0;
   out_1119877989261778800[238] = 0.0;
   out_1119877989261778800[239] = 0.0;
   out_1119877989261778800[240] = 0.0;
   out_1119877989261778800[241] = 0.0;
   out_1119877989261778800[242] = 0.0;
   out_1119877989261778800[243] = 0.0;
   out_1119877989261778800[244] = 0.0;
   out_1119877989261778800[245] = 0.0;
   out_1119877989261778800[246] = 0.0;
   out_1119877989261778800[247] = 1.0;
   out_1119877989261778800[248] = 0.0;
   out_1119877989261778800[249] = 0.0;
   out_1119877989261778800[250] = 0.0;
   out_1119877989261778800[251] = 0.0;
   out_1119877989261778800[252] = 0.0;
   out_1119877989261778800[253] = 0.0;
   out_1119877989261778800[254] = 0.0;
   out_1119877989261778800[255] = 0.0;
   out_1119877989261778800[256] = 0.0;
   out_1119877989261778800[257] = 0.0;
   out_1119877989261778800[258] = 0.0;
   out_1119877989261778800[259] = 0.0;
   out_1119877989261778800[260] = 0.0;
   out_1119877989261778800[261] = 0.0;
   out_1119877989261778800[262] = 0.0;
   out_1119877989261778800[263] = 0.0;
   out_1119877989261778800[264] = 0.0;
   out_1119877989261778800[265] = 0.0;
   out_1119877989261778800[266] = 1.0;
   out_1119877989261778800[267] = 0.0;
   out_1119877989261778800[268] = 0.0;
   out_1119877989261778800[269] = 0.0;
   out_1119877989261778800[270] = 0.0;
   out_1119877989261778800[271] = 0.0;
   out_1119877989261778800[272] = 0.0;
   out_1119877989261778800[273] = 0.0;
   out_1119877989261778800[274] = 0.0;
   out_1119877989261778800[275] = 0.0;
   out_1119877989261778800[276] = 0.0;
   out_1119877989261778800[277] = 0.0;
   out_1119877989261778800[278] = 0.0;
   out_1119877989261778800[279] = 0.0;
   out_1119877989261778800[280] = 0.0;
   out_1119877989261778800[281] = 0.0;
   out_1119877989261778800[282] = 0.0;
   out_1119877989261778800[283] = 0.0;
   out_1119877989261778800[284] = 0.0;
   out_1119877989261778800[285] = 1.0;
   out_1119877989261778800[286] = 0.0;
   out_1119877989261778800[287] = 0.0;
   out_1119877989261778800[288] = 0.0;
   out_1119877989261778800[289] = 0.0;
   out_1119877989261778800[290] = 0.0;
   out_1119877989261778800[291] = 0.0;
   out_1119877989261778800[292] = 0.0;
   out_1119877989261778800[293] = 0.0;
   out_1119877989261778800[294] = 0.0;
   out_1119877989261778800[295] = 0.0;
   out_1119877989261778800[296] = 0.0;
   out_1119877989261778800[297] = 0.0;
   out_1119877989261778800[298] = 0.0;
   out_1119877989261778800[299] = 0.0;
   out_1119877989261778800[300] = 0.0;
   out_1119877989261778800[301] = 0.0;
   out_1119877989261778800[302] = 0.0;
   out_1119877989261778800[303] = 0.0;
   out_1119877989261778800[304] = 1.0;
   out_1119877989261778800[305] = 0.0;
   out_1119877989261778800[306] = 0.0;
   out_1119877989261778800[307] = 0.0;
   out_1119877989261778800[308] = 0.0;
   out_1119877989261778800[309] = 0.0;
   out_1119877989261778800[310] = 0.0;
   out_1119877989261778800[311] = 0.0;
   out_1119877989261778800[312] = 0.0;
   out_1119877989261778800[313] = 0.0;
   out_1119877989261778800[314] = 0.0;
   out_1119877989261778800[315] = 0.0;
   out_1119877989261778800[316] = 0.0;
   out_1119877989261778800[317] = 0.0;
   out_1119877989261778800[318] = 0.0;
   out_1119877989261778800[319] = 0.0;
   out_1119877989261778800[320] = 0.0;
   out_1119877989261778800[321] = 0.0;
   out_1119877989261778800[322] = 0.0;
   out_1119877989261778800[323] = 1.0;
}
void f_fun(double *state, double dt, double *out_2123753475159758437) {
   out_2123753475159758437[0] = atan2((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), -(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]));
   out_2123753475159758437[1] = asin(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]));
   out_2123753475159758437[2] = atan2(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), -(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]));
   out_2123753475159758437[3] = dt*state[12] + state[3];
   out_2123753475159758437[4] = dt*state[13] + state[4];
   out_2123753475159758437[5] = dt*state[14] + state[5];
   out_2123753475159758437[6] = state[6];
   out_2123753475159758437[7] = state[7];
   out_2123753475159758437[8] = state[8];
   out_2123753475159758437[9] = state[9];
   out_2123753475159758437[10] = state[10];
   out_2123753475159758437[11] = state[11];
   out_2123753475159758437[12] = state[12];
   out_2123753475159758437[13] = state[13];
   out_2123753475159758437[14] = state[14];
   out_2123753475159758437[15] = state[15];
   out_2123753475159758437[16] = state[16];
   out_2123753475159758437[17] = state[17];
}
void F_fun(double *state, double dt, double *out_2042072363153328823) {
   out_2042072363153328823[0] = ((-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*cos(state[0])*cos(state[1]) - sin(state[0])*cos(dt*state[6])*cos(dt*state[7])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + ((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*cos(state[0])*cos(state[1]) - sin(dt*state[6])*sin(state[0])*cos(dt*state[7])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_2042072363153328823[1] = ((-sin(dt*state[6])*sin(dt*state[8]) - sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*cos(state[1]) - (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*sin(state[1]) - sin(state[1])*cos(dt*state[6])*cos(dt*state[7])*cos(state[0]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*sin(state[1]) + (-sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) + sin(dt*state[8])*cos(dt*state[6]))*cos(state[1]) - sin(dt*state[6])*sin(state[1])*cos(dt*state[7])*cos(state[0]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_2042072363153328823[2] = 0;
   out_2042072363153328823[3] = 0;
   out_2042072363153328823[4] = 0;
   out_2042072363153328823[5] = 0;
   out_2042072363153328823[6] = (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(dt*cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*sin(dt*state[8]) - dt*sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-dt*sin(dt*state[6])*cos(dt*state[8]) + dt*sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) - dt*cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (dt*sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_2042072363153328823[7] = (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[6])*sin(dt*state[7])*cos(state[0])*cos(state[1]) + dt*sin(dt*state[6])*sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) - dt*sin(dt*state[6])*sin(state[1])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[7])*cos(dt*state[6])*cos(state[0])*cos(state[1]) + dt*sin(dt*state[8])*sin(state[0])*cos(dt*state[6])*cos(dt*state[7])*cos(state[1]) - dt*sin(state[1])*cos(dt*state[6])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_2042072363153328823[8] = ((dt*sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + dt*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (dt*sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + ((dt*sin(dt*state[6])*sin(dt*state[8]) + dt*sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*cos(dt*state[8]) + dt*sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_2042072363153328823[9] = 0;
   out_2042072363153328823[10] = 0;
   out_2042072363153328823[11] = 0;
   out_2042072363153328823[12] = 0;
   out_2042072363153328823[13] = 0;
   out_2042072363153328823[14] = 0;
   out_2042072363153328823[15] = 0;
   out_2042072363153328823[16] = 0;
   out_2042072363153328823[17] = 0;
   out_2042072363153328823[18] = (-sin(dt*state[7])*sin(state[0])*cos(state[1]) - sin(dt*state[8])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_2042072363153328823[19] = (-sin(dt*state[7])*sin(state[1])*cos(state[0]) + sin(dt*state[8])*sin(state[0])*sin(state[1])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_2042072363153328823[20] = 0;
   out_2042072363153328823[21] = 0;
   out_2042072363153328823[22] = 0;
   out_2042072363153328823[23] = 0;
   out_2042072363153328823[24] = 0;
   out_2042072363153328823[25] = (dt*sin(dt*state[7])*sin(dt*state[8])*sin(state[0])*cos(state[1]) - dt*sin(dt*state[7])*sin(state[1])*cos(dt*state[8]) + dt*cos(dt*state[7])*cos(state[0])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_2042072363153328823[26] = (-dt*sin(dt*state[8])*sin(state[1])*cos(dt*state[7]) - dt*sin(state[0])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_2042072363153328823[27] = 0;
   out_2042072363153328823[28] = 0;
   out_2042072363153328823[29] = 0;
   out_2042072363153328823[30] = 0;
   out_2042072363153328823[31] = 0;
   out_2042072363153328823[32] = 0;
   out_2042072363153328823[33] = 0;
   out_2042072363153328823[34] = 0;
   out_2042072363153328823[35] = 0;
   out_2042072363153328823[36] = ((sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[7]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[7]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_2042072363153328823[37] = (-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(-sin(dt*state[7])*sin(state[2])*cos(state[0])*cos(state[1]) + sin(dt*state[8])*sin(state[0])*sin(state[2])*cos(dt*state[7])*cos(state[1]) - sin(state[1])*sin(state[2])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*(-sin(dt*state[7])*cos(state[0])*cos(state[1])*cos(state[2]) + sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1])*cos(state[2]) - sin(state[1])*cos(dt*state[7])*cos(dt*state[8])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_2042072363153328823[38] = ((-sin(state[0])*sin(state[2]) - sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (-sin(state[0])*sin(state[1])*sin(state[2]) - cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_2042072363153328823[39] = 0;
   out_2042072363153328823[40] = 0;
   out_2042072363153328823[41] = 0;
   out_2042072363153328823[42] = 0;
   out_2042072363153328823[43] = (-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(dt*(sin(state[0])*cos(state[2]) - sin(state[1])*sin(state[2])*cos(state[0]))*cos(dt*state[7]) - dt*(sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[7])*sin(dt*state[8]) - dt*sin(dt*state[7])*sin(state[2])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*(dt*(-sin(state[0])*sin(state[2]) - sin(state[1])*cos(state[0])*cos(state[2]))*cos(dt*state[7]) - dt*(sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[7])*sin(dt*state[8]) - dt*sin(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_2042072363153328823[44] = (dt*(sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*cos(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*sin(state[2])*cos(dt*state[7])*cos(state[1]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + (dt*(sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*cos(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[7])*cos(state[1])*cos(state[2]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_2042072363153328823[45] = 0;
   out_2042072363153328823[46] = 0;
   out_2042072363153328823[47] = 0;
   out_2042072363153328823[48] = 0;
   out_2042072363153328823[49] = 0;
   out_2042072363153328823[50] = 0;
   out_2042072363153328823[51] = 0;
   out_2042072363153328823[52] = 0;
   out_2042072363153328823[53] = 0;
   out_2042072363153328823[54] = 0;
   out_2042072363153328823[55] = 0;
   out_2042072363153328823[56] = 0;
   out_2042072363153328823[57] = 1;
   out_2042072363153328823[58] = 0;
   out_2042072363153328823[59] = 0;
   out_2042072363153328823[60] = 0;
   out_2042072363153328823[61] = 0;
   out_2042072363153328823[62] = 0;
   out_2042072363153328823[63] = 0;
   out_2042072363153328823[64] = 0;
   out_2042072363153328823[65] = 0;
   out_2042072363153328823[66] = dt;
   out_2042072363153328823[67] = 0;
   out_2042072363153328823[68] = 0;
   out_2042072363153328823[69] = 0;
   out_2042072363153328823[70] = 0;
   out_2042072363153328823[71] = 0;
   out_2042072363153328823[72] = 0;
   out_2042072363153328823[73] = 0;
   out_2042072363153328823[74] = 0;
   out_2042072363153328823[75] = 0;
   out_2042072363153328823[76] = 1;
   out_2042072363153328823[77] = 0;
   out_2042072363153328823[78] = 0;
   out_2042072363153328823[79] = 0;
   out_2042072363153328823[80] = 0;
   out_2042072363153328823[81] = 0;
   out_2042072363153328823[82] = 0;
   out_2042072363153328823[83] = 0;
   out_2042072363153328823[84] = 0;
   out_2042072363153328823[85] = dt;
   out_2042072363153328823[86] = 0;
   out_2042072363153328823[87] = 0;
   out_2042072363153328823[88] = 0;
   out_2042072363153328823[89] = 0;
   out_2042072363153328823[90] = 0;
   out_2042072363153328823[91] = 0;
   out_2042072363153328823[92] = 0;
   out_2042072363153328823[93] = 0;
   out_2042072363153328823[94] = 0;
   out_2042072363153328823[95] = 1;
   out_2042072363153328823[96] = 0;
   out_2042072363153328823[97] = 0;
   out_2042072363153328823[98] = 0;
   out_2042072363153328823[99] = 0;
   out_2042072363153328823[100] = 0;
   out_2042072363153328823[101] = 0;
   out_2042072363153328823[102] = 0;
   out_2042072363153328823[103] = 0;
   out_2042072363153328823[104] = dt;
   out_2042072363153328823[105] = 0;
   out_2042072363153328823[106] = 0;
   out_2042072363153328823[107] = 0;
   out_2042072363153328823[108] = 0;
   out_2042072363153328823[109] = 0;
   out_2042072363153328823[110] = 0;
   out_2042072363153328823[111] = 0;
   out_2042072363153328823[112] = 0;
   out_2042072363153328823[113] = 0;
   out_2042072363153328823[114] = 1;
   out_2042072363153328823[115] = 0;
   out_2042072363153328823[116] = 0;
   out_2042072363153328823[117] = 0;
   out_2042072363153328823[118] = 0;
   out_2042072363153328823[119] = 0;
   out_2042072363153328823[120] = 0;
   out_2042072363153328823[121] = 0;
   out_2042072363153328823[122] = 0;
   out_2042072363153328823[123] = 0;
   out_2042072363153328823[124] = 0;
   out_2042072363153328823[125] = 0;
   out_2042072363153328823[126] = 0;
   out_2042072363153328823[127] = 0;
   out_2042072363153328823[128] = 0;
   out_2042072363153328823[129] = 0;
   out_2042072363153328823[130] = 0;
   out_2042072363153328823[131] = 0;
   out_2042072363153328823[132] = 0;
   out_2042072363153328823[133] = 1;
   out_2042072363153328823[134] = 0;
   out_2042072363153328823[135] = 0;
   out_2042072363153328823[136] = 0;
   out_2042072363153328823[137] = 0;
   out_2042072363153328823[138] = 0;
   out_2042072363153328823[139] = 0;
   out_2042072363153328823[140] = 0;
   out_2042072363153328823[141] = 0;
   out_2042072363153328823[142] = 0;
   out_2042072363153328823[143] = 0;
   out_2042072363153328823[144] = 0;
   out_2042072363153328823[145] = 0;
   out_2042072363153328823[146] = 0;
   out_2042072363153328823[147] = 0;
   out_2042072363153328823[148] = 0;
   out_2042072363153328823[149] = 0;
   out_2042072363153328823[150] = 0;
   out_2042072363153328823[151] = 0;
   out_2042072363153328823[152] = 1;
   out_2042072363153328823[153] = 0;
   out_2042072363153328823[154] = 0;
   out_2042072363153328823[155] = 0;
   out_2042072363153328823[156] = 0;
   out_2042072363153328823[157] = 0;
   out_2042072363153328823[158] = 0;
   out_2042072363153328823[159] = 0;
   out_2042072363153328823[160] = 0;
   out_2042072363153328823[161] = 0;
   out_2042072363153328823[162] = 0;
   out_2042072363153328823[163] = 0;
   out_2042072363153328823[164] = 0;
   out_2042072363153328823[165] = 0;
   out_2042072363153328823[166] = 0;
   out_2042072363153328823[167] = 0;
   out_2042072363153328823[168] = 0;
   out_2042072363153328823[169] = 0;
   out_2042072363153328823[170] = 0;
   out_2042072363153328823[171] = 1;
   out_2042072363153328823[172] = 0;
   out_2042072363153328823[173] = 0;
   out_2042072363153328823[174] = 0;
   out_2042072363153328823[175] = 0;
   out_2042072363153328823[176] = 0;
   out_2042072363153328823[177] = 0;
   out_2042072363153328823[178] = 0;
   out_2042072363153328823[179] = 0;
   out_2042072363153328823[180] = 0;
   out_2042072363153328823[181] = 0;
   out_2042072363153328823[182] = 0;
   out_2042072363153328823[183] = 0;
   out_2042072363153328823[184] = 0;
   out_2042072363153328823[185] = 0;
   out_2042072363153328823[186] = 0;
   out_2042072363153328823[187] = 0;
   out_2042072363153328823[188] = 0;
   out_2042072363153328823[189] = 0;
   out_2042072363153328823[190] = 1;
   out_2042072363153328823[191] = 0;
   out_2042072363153328823[192] = 0;
   out_2042072363153328823[193] = 0;
   out_2042072363153328823[194] = 0;
   out_2042072363153328823[195] = 0;
   out_2042072363153328823[196] = 0;
   out_2042072363153328823[197] = 0;
   out_2042072363153328823[198] = 0;
   out_2042072363153328823[199] = 0;
   out_2042072363153328823[200] = 0;
   out_2042072363153328823[201] = 0;
   out_2042072363153328823[202] = 0;
   out_2042072363153328823[203] = 0;
   out_2042072363153328823[204] = 0;
   out_2042072363153328823[205] = 0;
   out_2042072363153328823[206] = 0;
   out_2042072363153328823[207] = 0;
   out_2042072363153328823[208] = 0;
   out_2042072363153328823[209] = 1;
   out_2042072363153328823[210] = 0;
   out_2042072363153328823[211] = 0;
   out_2042072363153328823[212] = 0;
   out_2042072363153328823[213] = 0;
   out_2042072363153328823[214] = 0;
   out_2042072363153328823[215] = 0;
   out_2042072363153328823[216] = 0;
   out_2042072363153328823[217] = 0;
   out_2042072363153328823[218] = 0;
   out_2042072363153328823[219] = 0;
   out_2042072363153328823[220] = 0;
   out_2042072363153328823[221] = 0;
   out_2042072363153328823[222] = 0;
   out_2042072363153328823[223] = 0;
   out_2042072363153328823[224] = 0;
   out_2042072363153328823[225] = 0;
   out_2042072363153328823[226] = 0;
   out_2042072363153328823[227] = 0;
   out_2042072363153328823[228] = 1;
   out_2042072363153328823[229] = 0;
   out_2042072363153328823[230] = 0;
   out_2042072363153328823[231] = 0;
   out_2042072363153328823[232] = 0;
   out_2042072363153328823[233] = 0;
   out_2042072363153328823[234] = 0;
   out_2042072363153328823[235] = 0;
   out_2042072363153328823[236] = 0;
   out_2042072363153328823[237] = 0;
   out_2042072363153328823[238] = 0;
   out_2042072363153328823[239] = 0;
   out_2042072363153328823[240] = 0;
   out_2042072363153328823[241] = 0;
   out_2042072363153328823[242] = 0;
   out_2042072363153328823[243] = 0;
   out_2042072363153328823[244] = 0;
   out_2042072363153328823[245] = 0;
   out_2042072363153328823[246] = 0;
   out_2042072363153328823[247] = 1;
   out_2042072363153328823[248] = 0;
   out_2042072363153328823[249] = 0;
   out_2042072363153328823[250] = 0;
   out_2042072363153328823[251] = 0;
   out_2042072363153328823[252] = 0;
   out_2042072363153328823[253] = 0;
   out_2042072363153328823[254] = 0;
   out_2042072363153328823[255] = 0;
   out_2042072363153328823[256] = 0;
   out_2042072363153328823[257] = 0;
   out_2042072363153328823[258] = 0;
   out_2042072363153328823[259] = 0;
   out_2042072363153328823[260] = 0;
   out_2042072363153328823[261] = 0;
   out_2042072363153328823[262] = 0;
   out_2042072363153328823[263] = 0;
   out_2042072363153328823[264] = 0;
   out_2042072363153328823[265] = 0;
   out_2042072363153328823[266] = 1;
   out_2042072363153328823[267] = 0;
   out_2042072363153328823[268] = 0;
   out_2042072363153328823[269] = 0;
   out_2042072363153328823[270] = 0;
   out_2042072363153328823[271] = 0;
   out_2042072363153328823[272] = 0;
   out_2042072363153328823[273] = 0;
   out_2042072363153328823[274] = 0;
   out_2042072363153328823[275] = 0;
   out_2042072363153328823[276] = 0;
   out_2042072363153328823[277] = 0;
   out_2042072363153328823[278] = 0;
   out_2042072363153328823[279] = 0;
   out_2042072363153328823[280] = 0;
   out_2042072363153328823[281] = 0;
   out_2042072363153328823[282] = 0;
   out_2042072363153328823[283] = 0;
   out_2042072363153328823[284] = 0;
   out_2042072363153328823[285] = 1;
   out_2042072363153328823[286] = 0;
   out_2042072363153328823[287] = 0;
   out_2042072363153328823[288] = 0;
   out_2042072363153328823[289] = 0;
   out_2042072363153328823[290] = 0;
   out_2042072363153328823[291] = 0;
   out_2042072363153328823[292] = 0;
   out_2042072363153328823[293] = 0;
   out_2042072363153328823[294] = 0;
   out_2042072363153328823[295] = 0;
   out_2042072363153328823[296] = 0;
   out_2042072363153328823[297] = 0;
   out_2042072363153328823[298] = 0;
   out_2042072363153328823[299] = 0;
   out_2042072363153328823[300] = 0;
   out_2042072363153328823[301] = 0;
   out_2042072363153328823[302] = 0;
   out_2042072363153328823[303] = 0;
   out_2042072363153328823[304] = 1;
   out_2042072363153328823[305] = 0;
   out_2042072363153328823[306] = 0;
   out_2042072363153328823[307] = 0;
   out_2042072363153328823[308] = 0;
   out_2042072363153328823[309] = 0;
   out_2042072363153328823[310] = 0;
   out_2042072363153328823[311] = 0;
   out_2042072363153328823[312] = 0;
   out_2042072363153328823[313] = 0;
   out_2042072363153328823[314] = 0;
   out_2042072363153328823[315] = 0;
   out_2042072363153328823[316] = 0;
   out_2042072363153328823[317] = 0;
   out_2042072363153328823[318] = 0;
   out_2042072363153328823[319] = 0;
   out_2042072363153328823[320] = 0;
   out_2042072363153328823[321] = 0;
   out_2042072363153328823[322] = 0;
   out_2042072363153328823[323] = 1;
}
void h_4(double *state, double *unused, double *out_2017169174657903512) {
   out_2017169174657903512[0] = state[6] + state[9];
   out_2017169174657903512[1] = state[7] + state[10];
   out_2017169174657903512[2] = state[8] + state[11];
}
void H_4(double *state, double *unused, double *out_2651929220582128772) {
   out_2651929220582128772[0] = 0;
   out_2651929220582128772[1] = 0;
   out_2651929220582128772[2] = 0;
   out_2651929220582128772[3] = 0;
   out_2651929220582128772[4] = 0;
   out_2651929220582128772[5] = 0;
   out_2651929220582128772[6] = 1;
   out_2651929220582128772[7] = 0;
   out_2651929220582128772[8] = 0;
   out_2651929220582128772[9] = 1;
   out_2651929220582128772[10] = 0;
   out_2651929220582128772[11] = 0;
   out_2651929220582128772[12] = 0;
   out_2651929220582128772[13] = 0;
   out_2651929220582128772[14] = 0;
   out_2651929220582128772[15] = 0;
   out_2651929220582128772[16] = 0;
   out_2651929220582128772[17] = 0;
   out_2651929220582128772[18] = 0;
   out_2651929220582128772[19] = 0;
   out_2651929220582128772[20] = 0;
   out_2651929220582128772[21] = 0;
   out_2651929220582128772[22] = 0;
   out_2651929220582128772[23] = 0;
   out_2651929220582128772[24] = 0;
   out_2651929220582128772[25] = 1;
   out_2651929220582128772[26] = 0;
   out_2651929220582128772[27] = 0;
   out_2651929220582128772[28] = 1;
   out_2651929220582128772[29] = 0;
   out_2651929220582128772[30] = 0;
   out_2651929220582128772[31] = 0;
   out_2651929220582128772[32] = 0;
   out_2651929220582128772[33] = 0;
   out_2651929220582128772[34] = 0;
   out_2651929220582128772[35] = 0;
   out_2651929220582128772[36] = 0;
   out_2651929220582128772[37] = 0;
   out_2651929220582128772[38] = 0;
   out_2651929220582128772[39] = 0;
   out_2651929220582128772[40] = 0;
   out_2651929220582128772[41] = 0;
   out_2651929220582128772[42] = 0;
   out_2651929220582128772[43] = 0;
   out_2651929220582128772[44] = 1;
   out_2651929220582128772[45] = 0;
   out_2651929220582128772[46] = 0;
   out_2651929220582128772[47] = 1;
   out_2651929220582128772[48] = 0;
   out_2651929220582128772[49] = 0;
   out_2651929220582128772[50] = 0;
   out_2651929220582128772[51] = 0;
   out_2651929220582128772[52] = 0;
   out_2651929220582128772[53] = 0;
}
void h_10(double *state, double *unused, double *out_7790822241274132646) {
   out_7790822241274132646[0] = 9.8100000000000005*sin(state[1]) - state[4]*state[8] + state[5]*state[7] + state[12] + state[15];
   out_7790822241274132646[1] = -9.8100000000000005*sin(state[0])*cos(state[1]) + state[3]*state[8] - state[5]*state[6] + state[13] + state[16];
   out_7790822241274132646[2] = -9.8100000000000005*cos(state[0])*cos(state[1]) - state[3]*state[7] + state[4]*state[6] + state[14] + state[17];
}
void H_10(double *state, double *unused, double *out_1807588708691679220) {
   out_1807588708691679220[0] = 0;
   out_1807588708691679220[1] = 9.8100000000000005*cos(state[1]);
   out_1807588708691679220[2] = 0;
   out_1807588708691679220[3] = 0;
   out_1807588708691679220[4] = -state[8];
   out_1807588708691679220[5] = state[7];
   out_1807588708691679220[6] = 0;
   out_1807588708691679220[7] = state[5];
   out_1807588708691679220[8] = -state[4];
   out_1807588708691679220[9] = 0;
   out_1807588708691679220[10] = 0;
   out_1807588708691679220[11] = 0;
   out_1807588708691679220[12] = 1;
   out_1807588708691679220[13] = 0;
   out_1807588708691679220[14] = 0;
   out_1807588708691679220[15] = 1;
   out_1807588708691679220[16] = 0;
   out_1807588708691679220[17] = 0;
   out_1807588708691679220[18] = -9.8100000000000005*cos(state[0])*cos(state[1]);
   out_1807588708691679220[19] = 9.8100000000000005*sin(state[0])*sin(state[1]);
   out_1807588708691679220[20] = 0;
   out_1807588708691679220[21] = state[8];
   out_1807588708691679220[22] = 0;
   out_1807588708691679220[23] = -state[6];
   out_1807588708691679220[24] = -state[5];
   out_1807588708691679220[25] = 0;
   out_1807588708691679220[26] = state[3];
   out_1807588708691679220[27] = 0;
   out_1807588708691679220[28] = 0;
   out_1807588708691679220[29] = 0;
   out_1807588708691679220[30] = 0;
   out_1807588708691679220[31] = 1;
   out_1807588708691679220[32] = 0;
   out_1807588708691679220[33] = 0;
   out_1807588708691679220[34] = 1;
   out_1807588708691679220[35] = 0;
   out_1807588708691679220[36] = 9.8100000000000005*sin(state[0])*cos(state[1]);
   out_1807588708691679220[37] = 9.8100000000000005*sin(state[1])*cos(state[0]);
   out_1807588708691679220[38] = 0;
   out_1807588708691679220[39] = -state[7];
   out_1807588708691679220[40] = state[6];
   out_1807588708691679220[41] = 0;
   out_1807588708691679220[42] = state[4];
   out_1807588708691679220[43] = -state[3];
   out_1807588708691679220[44] = 0;
   out_1807588708691679220[45] = 0;
   out_1807588708691679220[46] = 0;
   out_1807588708691679220[47] = 0;
   out_1807588708691679220[48] = 0;
   out_1807588708691679220[49] = 0;
   out_1807588708691679220[50] = 1;
   out_1807588708691679220[51] = 0;
   out_1807588708691679220[52] = 0;
   out_1807588708691679220[53] = 1;
}
void h_13(double *state, double *unused, double *out_5087328461209279336) {
   out_5087328461209279336[0] = state[3];
   out_5087328461209279336[1] = state[4];
   out_5087328461209279336[2] = state[5];
}
void H_13(double *state, double *unused, double *out_5864203045914461573) {
   out_5864203045914461573[0] = 0;
   out_5864203045914461573[1] = 0;
   out_5864203045914461573[2] = 0;
   out_5864203045914461573[3] = 1;
   out_5864203045914461573[4] = 0;
   out_5864203045914461573[5] = 0;
   out_5864203045914461573[6] = 0;
   out_5864203045914461573[7] = 0;
   out_5864203045914461573[8] = 0;
   out_5864203045914461573[9] = 0;
   out_5864203045914461573[10] = 0;
   out_5864203045914461573[11] = 0;
   out_5864203045914461573[12] = 0;
   out_5864203045914461573[13] = 0;
   out_5864203045914461573[14] = 0;
   out_5864203045914461573[15] = 0;
   out_5864203045914461573[16] = 0;
   out_5864203045914461573[17] = 0;
   out_5864203045914461573[18] = 0;
   out_5864203045914461573[19] = 0;
   out_5864203045914461573[20] = 0;
   out_5864203045914461573[21] = 0;
   out_5864203045914461573[22] = 1;
   out_5864203045914461573[23] = 0;
   out_5864203045914461573[24] = 0;
   out_5864203045914461573[25] = 0;
   out_5864203045914461573[26] = 0;
   out_5864203045914461573[27] = 0;
   out_5864203045914461573[28] = 0;
   out_5864203045914461573[29] = 0;
   out_5864203045914461573[30] = 0;
   out_5864203045914461573[31] = 0;
   out_5864203045914461573[32] = 0;
   out_5864203045914461573[33] = 0;
   out_5864203045914461573[34] = 0;
   out_5864203045914461573[35] = 0;
   out_5864203045914461573[36] = 0;
   out_5864203045914461573[37] = 0;
   out_5864203045914461573[38] = 0;
   out_5864203045914461573[39] = 0;
   out_5864203045914461573[40] = 0;
   out_5864203045914461573[41] = 1;
   out_5864203045914461573[42] = 0;
   out_5864203045914461573[43] = 0;
   out_5864203045914461573[44] = 0;
   out_5864203045914461573[45] = 0;
   out_5864203045914461573[46] = 0;
   out_5864203045914461573[47] = 0;
   out_5864203045914461573[48] = 0;
   out_5864203045914461573[49] = 0;
   out_5864203045914461573[50] = 0;
   out_5864203045914461573[51] = 0;
   out_5864203045914461573[52] = 0;
   out_5864203045914461573[53] = 0;
}
void h_14(double *state, double *unused, double *out_8996928075667050682) {
   out_8996928075667050682[0] = state[6];
   out_8996928075667050682[1] = state[7];
   out_8996928075667050682[2] = state[8];
}
void H_14(double *state, double *unused, double *out_6615170076921613301) {
   out_6615170076921613301[0] = 0;
   out_6615170076921613301[1] = 0;
   out_6615170076921613301[2] = 0;
   out_6615170076921613301[3] = 0;
   out_6615170076921613301[4] = 0;
   out_6615170076921613301[5] = 0;
   out_6615170076921613301[6] = 1;
   out_6615170076921613301[7] = 0;
   out_6615170076921613301[8] = 0;
   out_6615170076921613301[9] = 0;
   out_6615170076921613301[10] = 0;
   out_6615170076921613301[11] = 0;
   out_6615170076921613301[12] = 0;
   out_6615170076921613301[13] = 0;
   out_6615170076921613301[14] = 0;
   out_6615170076921613301[15] = 0;
   out_6615170076921613301[16] = 0;
   out_6615170076921613301[17] = 0;
   out_6615170076921613301[18] = 0;
   out_6615170076921613301[19] = 0;
   out_6615170076921613301[20] = 0;
   out_6615170076921613301[21] = 0;
   out_6615170076921613301[22] = 0;
   out_6615170076921613301[23] = 0;
   out_6615170076921613301[24] = 0;
   out_6615170076921613301[25] = 1;
   out_6615170076921613301[26] = 0;
   out_6615170076921613301[27] = 0;
   out_6615170076921613301[28] = 0;
   out_6615170076921613301[29] = 0;
   out_6615170076921613301[30] = 0;
   out_6615170076921613301[31] = 0;
   out_6615170076921613301[32] = 0;
   out_6615170076921613301[33] = 0;
   out_6615170076921613301[34] = 0;
   out_6615170076921613301[35] = 0;
   out_6615170076921613301[36] = 0;
   out_6615170076921613301[37] = 0;
   out_6615170076921613301[38] = 0;
   out_6615170076921613301[39] = 0;
   out_6615170076921613301[40] = 0;
   out_6615170076921613301[41] = 0;
   out_6615170076921613301[42] = 0;
   out_6615170076921613301[43] = 0;
   out_6615170076921613301[44] = 1;
   out_6615170076921613301[45] = 0;
   out_6615170076921613301[46] = 0;
   out_6615170076921613301[47] = 0;
   out_6615170076921613301[48] = 0;
   out_6615170076921613301[49] = 0;
   out_6615170076921613301[50] = 0;
   out_6615170076921613301[51] = 0;
   out_6615170076921613301[52] = 0;
   out_6615170076921613301[53] = 0;
}
#include <eigen3/Eigen/Dense>
#include <iostream>

typedef Eigen::Matrix<double, DIM, DIM, Eigen::RowMajor> DDM;
typedef Eigen::Matrix<double, EDIM, EDIM, Eigen::RowMajor> EEM;
typedef Eigen::Matrix<double, DIM, EDIM, Eigen::RowMajor> DEM;

void predict(double *in_x, double *in_P, double *in_Q, double dt) {
  typedef Eigen::Matrix<double, MEDIM, MEDIM, Eigen::RowMajor> RRM;

  double nx[DIM] = {0};
  double in_F[EDIM*EDIM] = {0};

  // functions from sympy
  f_fun(in_x, dt, nx);
  F_fun(in_x, dt, in_F);


  EEM F(in_F);
  EEM P(in_P);
  EEM Q(in_Q);

  RRM F_main = F.topLeftCorner(MEDIM, MEDIM);
  P.topLeftCorner(MEDIM, MEDIM) = (F_main * P.topLeftCorner(MEDIM, MEDIM)) * F_main.transpose();
  P.topRightCorner(MEDIM, EDIM - MEDIM) = F_main * P.topRightCorner(MEDIM, EDIM - MEDIM);
  P.bottomLeftCorner(EDIM - MEDIM, MEDIM) = P.bottomLeftCorner(EDIM - MEDIM, MEDIM) * F_main.transpose();

  P = P + dt*Q;

  // copy out state
  memcpy(in_x, nx, DIM * sizeof(double));
  memcpy(in_P, P.data(), EDIM * EDIM * sizeof(double));
}

// note: extra_args dim only correct when null space projecting
// otherwise 1
template <int ZDIM, int EADIM, bool MAHA_TEST>
void update(double *in_x, double *in_P, Hfun h_fun, Hfun H_fun, Hfun Hea_fun, double *in_z, double *in_R, double *in_ea, double MAHA_THRESHOLD) {
  typedef Eigen::Matrix<double, ZDIM, ZDIM, Eigen::RowMajor> ZZM;
  typedef Eigen::Matrix<double, ZDIM, DIM, Eigen::RowMajor> ZDM;
  typedef Eigen::Matrix<double, Eigen::Dynamic, EDIM, Eigen::RowMajor> XEM;
  //typedef Eigen::Matrix<double, EDIM, ZDIM, Eigen::RowMajor> EZM;
  typedef Eigen::Matrix<double, Eigen::Dynamic, 1> X1M;
  typedef Eigen::Matrix<double, Eigen::Dynamic, Eigen::Dynamic, Eigen::RowMajor> XXM;

  double in_hx[ZDIM] = {0};
  double in_H[ZDIM * DIM] = {0};
  double in_H_mod[EDIM * DIM] = {0};
  double delta_x[EDIM] = {0};
  double x_new[DIM] = {0};


  // state x, P
  Eigen::Matrix<double, ZDIM, 1> z(in_z);
  EEM P(in_P);
  ZZM pre_R(in_R);

  // functions from sympy
  h_fun(in_x, in_ea, in_hx);
  H_fun(in_x, in_ea, in_H);
  ZDM pre_H(in_H);

  // get y (y = z - hx)
  Eigen::Matrix<double, ZDIM, 1> pre_y(in_hx); pre_y = z - pre_y;
  X1M y; XXM H; XXM R;
  if (Hea_fun){
    typedef Eigen::Matrix<double, ZDIM, EADIM, Eigen::RowMajor> ZAM;
    double in_Hea[ZDIM * EADIM] = {0};
    Hea_fun(in_x, in_ea, in_Hea);
    ZAM Hea(in_Hea);
    XXM A = Hea.transpose().fullPivLu().kernel();


    y = A.transpose() * pre_y;
    H = A.transpose() * pre_H;
    R = A.transpose() * pre_R * A;
  } else {
    y = pre_y;
    H = pre_H;
    R = pre_R;
  }
  // get modified H
  H_mod_fun(in_x, in_H_mod);
  DEM H_mod(in_H_mod);
  XEM H_err = H * H_mod;

  // Do mahalobis distance test
  if (MAHA_TEST){
    XXM a = (H_err * P * H_err.transpose() + R).inverse();
    double maha_dist = y.transpose() * a * y;
    if (maha_dist > MAHA_THRESHOLD){
      R = 1.0e16 * R;
    }
  }

  // Outlier resilient weighting
  double weight = 1;//(1.5)/(1 + y.squaredNorm()/R.sum());

  // kalman gains and I_KH
  XXM S = ((H_err * P) * H_err.transpose()) + R/weight;
  XEM KT = S.fullPivLu().solve(H_err * P.transpose());
  //EZM K = KT.transpose(); TODO: WHY DOES THIS NOT COMPILE?
  //EZM K = S.fullPivLu().solve(H_err * P.transpose()).transpose();
  //std::cout << "Here is the matrix rot:\n" << K << std::endl;
  EEM I_KH = Eigen::Matrix<double, EDIM, EDIM>::Identity() - (KT.transpose() * H_err);

  // update state by injecting dx
  Eigen::Matrix<double, EDIM, 1> dx(delta_x);
  dx  = (KT.transpose() * y);
  memcpy(delta_x, dx.data(), EDIM * sizeof(double));
  err_fun(in_x, delta_x, x_new);
  Eigen::Matrix<double, DIM, 1> x(x_new);

  // update cov
  P = ((I_KH * P) * I_KH.transpose()) + ((KT.transpose() * R) * KT);

  // copy out state
  memcpy(in_x, x.data(), DIM * sizeof(double));
  memcpy(in_P, P.data(), EDIM * EDIM * sizeof(double));
  memcpy(in_z, y.data(), y.rows() * sizeof(double));
}




}
extern "C" {

void pose_update_4(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea) {
  update<3, 3, 0>(in_x, in_P, h_4, H_4, NULL, in_z, in_R, in_ea, MAHA_THRESH_4);
}
void pose_update_10(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea) {
  update<3, 3, 0>(in_x, in_P, h_10, H_10, NULL, in_z, in_R, in_ea, MAHA_THRESH_10);
}
void pose_update_13(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea) {
  update<3, 3, 0>(in_x, in_P, h_13, H_13, NULL, in_z, in_R, in_ea, MAHA_THRESH_13);
}
void pose_update_14(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea) {
  update<3, 3, 0>(in_x, in_P, h_14, H_14, NULL, in_z, in_R, in_ea, MAHA_THRESH_14);
}
void pose_err_fun(double *nom_x, double *delta_x, double *out_5635938807142857948) {
  err_fun(nom_x, delta_x, out_5635938807142857948);
}
void pose_inv_err_fun(double *nom_x, double *true_x, double *out_4989912554372507650) {
  inv_err_fun(nom_x, true_x, out_4989912554372507650);
}
void pose_H_mod_fun(double *state, double *out_1119877989261778800) {
  H_mod_fun(state, out_1119877989261778800);
}
void pose_f_fun(double *state, double dt, double *out_2123753475159758437) {
  f_fun(state,  dt, out_2123753475159758437);
}
void pose_F_fun(double *state, double dt, double *out_2042072363153328823) {
  F_fun(state,  dt, out_2042072363153328823);
}
void pose_h_4(double *state, double *unused, double *out_2017169174657903512) {
  h_4(state, unused, out_2017169174657903512);
}
void pose_H_4(double *state, double *unused, double *out_2651929220582128772) {
  H_4(state, unused, out_2651929220582128772);
}
void pose_h_10(double *state, double *unused, double *out_7790822241274132646) {
  h_10(state, unused, out_7790822241274132646);
}
void pose_H_10(double *state, double *unused, double *out_1807588708691679220) {
  H_10(state, unused, out_1807588708691679220);
}
void pose_h_13(double *state, double *unused, double *out_5087328461209279336) {
  h_13(state, unused, out_5087328461209279336);
}
void pose_H_13(double *state, double *unused, double *out_5864203045914461573) {
  H_13(state, unused, out_5864203045914461573);
}
void pose_h_14(double *state, double *unused, double *out_8996928075667050682) {
  h_14(state, unused, out_8996928075667050682);
}
void pose_H_14(double *state, double *unused, double *out_6615170076921613301) {
  H_14(state, unused, out_6615170076921613301);
}
void pose_predict(double *in_x, double *in_P, double *in_Q, double dt) {
  predict(in_x, in_P, in_Q, dt);
}
}

const EKF pose = {
  .name = "pose",
  .kinds = { 4, 10, 13, 14 },
  .feature_kinds = {  },
  .f_fun = pose_f_fun,
  .F_fun = pose_F_fun,
  .err_fun = pose_err_fun,
  .inv_err_fun = pose_inv_err_fun,
  .H_mod_fun = pose_H_mod_fun,
  .predict = pose_predict,
  .hs = {
    { 4, pose_h_4 },
    { 10, pose_h_10 },
    { 13, pose_h_13 },
    { 14, pose_h_14 },
  },
  .Hs = {
    { 4, pose_H_4 },
    { 10, pose_H_10 },
    { 13, pose_H_13 },
    { 14, pose_H_14 },
  },
  .updates = {
    { 4, pose_update_4 },
    { 10, pose_update_10 },
    { 13, pose_update_13 },
    { 14, pose_update_14 },
  },
  .Hes = {
  },
  .sets = {
  },
  .extra_routines = {
  },
};

ekf_lib_init(pose)
