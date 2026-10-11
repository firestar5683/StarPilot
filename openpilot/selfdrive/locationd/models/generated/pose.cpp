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
void err_fun(double *nom_x, double *delta_x, double *out_3762875391382386195) {
   out_3762875391382386195[0] = delta_x[0] + nom_x[0];
   out_3762875391382386195[1] = delta_x[1] + nom_x[1];
   out_3762875391382386195[2] = delta_x[2] + nom_x[2];
   out_3762875391382386195[3] = delta_x[3] + nom_x[3];
   out_3762875391382386195[4] = delta_x[4] + nom_x[4];
   out_3762875391382386195[5] = delta_x[5] + nom_x[5];
   out_3762875391382386195[6] = delta_x[6] + nom_x[6];
   out_3762875391382386195[7] = delta_x[7] + nom_x[7];
   out_3762875391382386195[8] = delta_x[8] + nom_x[8];
   out_3762875391382386195[9] = delta_x[9] + nom_x[9];
   out_3762875391382386195[10] = delta_x[10] + nom_x[10];
   out_3762875391382386195[11] = delta_x[11] + nom_x[11];
   out_3762875391382386195[12] = delta_x[12] + nom_x[12];
   out_3762875391382386195[13] = delta_x[13] + nom_x[13];
   out_3762875391382386195[14] = delta_x[14] + nom_x[14];
   out_3762875391382386195[15] = delta_x[15] + nom_x[15];
   out_3762875391382386195[16] = delta_x[16] + nom_x[16];
   out_3762875391382386195[17] = delta_x[17] + nom_x[17];
}
void inv_err_fun(double *nom_x, double *true_x, double *out_1907257459040696591) {
   out_1907257459040696591[0] = -nom_x[0] + true_x[0];
   out_1907257459040696591[1] = -nom_x[1] + true_x[1];
   out_1907257459040696591[2] = -nom_x[2] + true_x[2];
   out_1907257459040696591[3] = -nom_x[3] + true_x[3];
   out_1907257459040696591[4] = -nom_x[4] + true_x[4];
   out_1907257459040696591[5] = -nom_x[5] + true_x[5];
   out_1907257459040696591[6] = -nom_x[6] + true_x[6];
   out_1907257459040696591[7] = -nom_x[7] + true_x[7];
   out_1907257459040696591[8] = -nom_x[8] + true_x[8];
   out_1907257459040696591[9] = -nom_x[9] + true_x[9];
   out_1907257459040696591[10] = -nom_x[10] + true_x[10];
   out_1907257459040696591[11] = -nom_x[11] + true_x[11];
   out_1907257459040696591[12] = -nom_x[12] + true_x[12];
   out_1907257459040696591[13] = -nom_x[13] + true_x[13];
   out_1907257459040696591[14] = -nom_x[14] + true_x[14];
   out_1907257459040696591[15] = -nom_x[15] + true_x[15];
   out_1907257459040696591[16] = -nom_x[16] + true_x[16];
   out_1907257459040696591[17] = -nom_x[17] + true_x[17];
}
void H_mod_fun(double *state, double *out_4096443015319918083) {
   out_4096443015319918083[0] = 1.0;
   out_4096443015319918083[1] = 0.0;
   out_4096443015319918083[2] = 0.0;
   out_4096443015319918083[3] = 0.0;
   out_4096443015319918083[4] = 0.0;
   out_4096443015319918083[5] = 0.0;
   out_4096443015319918083[6] = 0.0;
   out_4096443015319918083[7] = 0.0;
   out_4096443015319918083[8] = 0.0;
   out_4096443015319918083[9] = 0.0;
   out_4096443015319918083[10] = 0.0;
   out_4096443015319918083[11] = 0.0;
   out_4096443015319918083[12] = 0.0;
   out_4096443015319918083[13] = 0.0;
   out_4096443015319918083[14] = 0.0;
   out_4096443015319918083[15] = 0.0;
   out_4096443015319918083[16] = 0.0;
   out_4096443015319918083[17] = 0.0;
   out_4096443015319918083[18] = 0.0;
   out_4096443015319918083[19] = 1.0;
   out_4096443015319918083[20] = 0.0;
   out_4096443015319918083[21] = 0.0;
   out_4096443015319918083[22] = 0.0;
   out_4096443015319918083[23] = 0.0;
   out_4096443015319918083[24] = 0.0;
   out_4096443015319918083[25] = 0.0;
   out_4096443015319918083[26] = 0.0;
   out_4096443015319918083[27] = 0.0;
   out_4096443015319918083[28] = 0.0;
   out_4096443015319918083[29] = 0.0;
   out_4096443015319918083[30] = 0.0;
   out_4096443015319918083[31] = 0.0;
   out_4096443015319918083[32] = 0.0;
   out_4096443015319918083[33] = 0.0;
   out_4096443015319918083[34] = 0.0;
   out_4096443015319918083[35] = 0.0;
   out_4096443015319918083[36] = 0.0;
   out_4096443015319918083[37] = 0.0;
   out_4096443015319918083[38] = 1.0;
   out_4096443015319918083[39] = 0.0;
   out_4096443015319918083[40] = 0.0;
   out_4096443015319918083[41] = 0.0;
   out_4096443015319918083[42] = 0.0;
   out_4096443015319918083[43] = 0.0;
   out_4096443015319918083[44] = 0.0;
   out_4096443015319918083[45] = 0.0;
   out_4096443015319918083[46] = 0.0;
   out_4096443015319918083[47] = 0.0;
   out_4096443015319918083[48] = 0.0;
   out_4096443015319918083[49] = 0.0;
   out_4096443015319918083[50] = 0.0;
   out_4096443015319918083[51] = 0.0;
   out_4096443015319918083[52] = 0.0;
   out_4096443015319918083[53] = 0.0;
   out_4096443015319918083[54] = 0.0;
   out_4096443015319918083[55] = 0.0;
   out_4096443015319918083[56] = 0.0;
   out_4096443015319918083[57] = 1.0;
   out_4096443015319918083[58] = 0.0;
   out_4096443015319918083[59] = 0.0;
   out_4096443015319918083[60] = 0.0;
   out_4096443015319918083[61] = 0.0;
   out_4096443015319918083[62] = 0.0;
   out_4096443015319918083[63] = 0.0;
   out_4096443015319918083[64] = 0.0;
   out_4096443015319918083[65] = 0.0;
   out_4096443015319918083[66] = 0.0;
   out_4096443015319918083[67] = 0.0;
   out_4096443015319918083[68] = 0.0;
   out_4096443015319918083[69] = 0.0;
   out_4096443015319918083[70] = 0.0;
   out_4096443015319918083[71] = 0.0;
   out_4096443015319918083[72] = 0.0;
   out_4096443015319918083[73] = 0.0;
   out_4096443015319918083[74] = 0.0;
   out_4096443015319918083[75] = 0.0;
   out_4096443015319918083[76] = 1.0;
   out_4096443015319918083[77] = 0.0;
   out_4096443015319918083[78] = 0.0;
   out_4096443015319918083[79] = 0.0;
   out_4096443015319918083[80] = 0.0;
   out_4096443015319918083[81] = 0.0;
   out_4096443015319918083[82] = 0.0;
   out_4096443015319918083[83] = 0.0;
   out_4096443015319918083[84] = 0.0;
   out_4096443015319918083[85] = 0.0;
   out_4096443015319918083[86] = 0.0;
   out_4096443015319918083[87] = 0.0;
   out_4096443015319918083[88] = 0.0;
   out_4096443015319918083[89] = 0.0;
   out_4096443015319918083[90] = 0.0;
   out_4096443015319918083[91] = 0.0;
   out_4096443015319918083[92] = 0.0;
   out_4096443015319918083[93] = 0.0;
   out_4096443015319918083[94] = 0.0;
   out_4096443015319918083[95] = 1.0;
   out_4096443015319918083[96] = 0.0;
   out_4096443015319918083[97] = 0.0;
   out_4096443015319918083[98] = 0.0;
   out_4096443015319918083[99] = 0.0;
   out_4096443015319918083[100] = 0.0;
   out_4096443015319918083[101] = 0.0;
   out_4096443015319918083[102] = 0.0;
   out_4096443015319918083[103] = 0.0;
   out_4096443015319918083[104] = 0.0;
   out_4096443015319918083[105] = 0.0;
   out_4096443015319918083[106] = 0.0;
   out_4096443015319918083[107] = 0.0;
   out_4096443015319918083[108] = 0.0;
   out_4096443015319918083[109] = 0.0;
   out_4096443015319918083[110] = 0.0;
   out_4096443015319918083[111] = 0.0;
   out_4096443015319918083[112] = 0.0;
   out_4096443015319918083[113] = 0.0;
   out_4096443015319918083[114] = 1.0;
   out_4096443015319918083[115] = 0.0;
   out_4096443015319918083[116] = 0.0;
   out_4096443015319918083[117] = 0.0;
   out_4096443015319918083[118] = 0.0;
   out_4096443015319918083[119] = 0.0;
   out_4096443015319918083[120] = 0.0;
   out_4096443015319918083[121] = 0.0;
   out_4096443015319918083[122] = 0.0;
   out_4096443015319918083[123] = 0.0;
   out_4096443015319918083[124] = 0.0;
   out_4096443015319918083[125] = 0.0;
   out_4096443015319918083[126] = 0.0;
   out_4096443015319918083[127] = 0.0;
   out_4096443015319918083[128] = 0.0;
   out_4096443015319918083[129] = 0.0;
   out_4096443015319918083[130] = 0.0;
   out_4096443015319918083[131] = 0.0;
   out_4096443015319918083[132] = 0.0;
   out_4096443015319918083[133] = 1.0;
   out_4096443015319918083[134] = 0.0;
   out_4096443015319918083[135] = 0.0;
   out_4096443015319918083[136] = 0.0;
   out_4096443015319918083[137] = 0.0;
   out_4096443015319918083[138] = 0.0;
   out_4096443015319918083[139] = 0.0;
   out_4096443015319918083[140] = 0.0;
   out_4096443015319918083[141] = 0.0;
   out_4096443015319918083[142] = 0.0;
   out_4096443015319918083[143] = 0.0;
   out_4096443015319918083[144] = 0.0;
   out_4096443015319918083[145] = 0.0;
   out_4096443015319918083[146] = 0.0;
   out_4096443015319918083[147] = 0.0;
   out_4096443015319918083[148] = 0.0;
   out_4096443015319918083[149] = 0.0;
   out_4096443015319918083[150] = 0.0;
   out_4096443015319918083[151] = 0.0;
   out_4096443015319918083[152] = 1.0;
   out_4096443015319918083[153] = 0.0;
   out_4096443015319918083[154] = 0.0;
   out_4096443015319918083[155] = 0.0;
   out_4096443015319918083[156] = 0.0;
   out_4096443015319918083[157] = 0.0;
   out_4096443015319918083[158] = 0.0;
   out_4096443015319918083[159] = 0.0;
   out_4096443015319918083[160] = 0.0;
   out_4096443015319918083[161] = 0.0;
   out_4096443015319918083[162] = 0.0;
   out_4096443015319918083[163] = 0.0;
   out_4096443015319918083[164] = 0.0;
   out_4096443015319918083[165] = 0.0;
   out_4096443015319918083[166] = 0.0;
   out_4096443015319918083[167] = 0.0;
   out_4096443015319918083[168] = 0.0;
   out_4096443015319918083[169] = 0.0;
   out_4096443015319918083[170] = 0.0;
   out_4096443015319918083[171] = 1.0;
   out_4096443015319918083[172] = 0.0;
   out_4096443015319918083[173] = 0.0;
   out_4096443015319918083[174] = 0.0;
   out_4096443015319918083[175] = 0.0;
   out_4096443015319918083[176] = 0.0;
   out_4096443015319918083[177] = 0.0;
   out_4096443015319918083[178] = 0.0;
   out_4096443015319918083[179] = 0.0;
   out_4096443015319918083[180] = 0.0;
   out_4096443015319918083[181] = 0.0;
   out_4096443015319918083[182] = 0.0;
   out_4096443015319918083[183] = 0.0;
   out_4096443015319918083[184] = 0.0;
   out_4096443015319918083[185] = 0.0;
   out_4096443015319918083[186] = 0.0;
   out_4096443015319918083[187] = 0.0;
   out_4096443015319918083[188] = 0.0;
   out_4096443015319918083[189] = 0.0;
   out_4096443015319918083[190] = 1.0;
   out_4096443015319918083[191] = 0.0;
   out_4096443015319918083[192] = 0.0;
   out_4096443015319918083[193] = 0.0;
   out_4096443015319918083[194] = 0.0;
   out_4096443015319918083[195] = 0.0;
   out_4096443015319918083[196] = 0.0;
   out_4096443015319918083[197] = 0.0;
   out_4096443015319918083[198] = 0.0;
   out_4096443015319918083[199] = 0.0;
   out_4096443015319918083[200] = 0.0;
   out_4096443015319918083[201] = 0.0;
   out_4096443015319918083[202] = 0.0;
   out_4096443015319918083[203] = 0.0;
   out_4096443015319918083[204] = 0.0;
   out_4096443015319918083[205] = 0.0;
   out_4096443015319918083[206] = 0.0;
   out_4096443015319918083[207] = 0.0;
   out_4096443015319918083[208] = 0.0;
   out_4096443015319918083[209] = 1.0;
   out_4096443015319918083[210] = 0.0;
   out_4096443015319918083[211] = 0.0;
   out_4096443015319918083[212] = 0.0;
   out_4096443015319918083[213] = 0.0;
   out_4096443015319918083[214] = 0.0;
   out_4096443015319918083[215] = 0.0;
   out_4096443015319918083[216] = 0.0;
   out_4096443015319918083[217] = 0.0;
   out_4096443015319918083[218] = 0.0;
   out_4096443015319918083[219] = 0.0;
   out_4096443015319918083[220] = 0.0;
   out_4096443015319918083[221] = 0.0;
   out_4096443015319918083[222] = 0.0;
   out_4096443015319918083[223] = 0.0;
   out_4096443015319918083[224] = 0.0;
   out_4096443015319918083[225] = 0.0;
   out_4096443015319918083[226] = 0.0;
   out_4096443015319918083[227] = 0.0;
   out_4096443015319918083[228] = 1.0;
   out_4096443015319918083[229] = 0.0;
   out_4096443015319918083[230] = 0.0;
   out_4096443015319918083[231] = 0.0;
   out_4096443015319918083[232] = 0.0;
   out_4096443015319918083[233] = 0.0;
   out_4096443015319918083[234] = 0.0;
   out_4096443015319918083[235] = 0.0;
   out_4096443015319918083[236] = 0.0;
   out_4096443015319918083[237] = 0.0;
   out_4096443015319918083[238] = 0.0;
   out_4096443015319918083[239] = 0.0;
   out_4096443015319918083[240] = 0.0;
   out_4096443015319918083[241] = 0.0;
   out_4096443015319918083[242] = 0.0;
   out_4096443015319918083[243] = 0.0;
   out_4096443015319918083[244] = 0.0;
   out_4096443015319918083[245] = 0.0;
   out_4096443015319918083[246] = 0.0;
   out_4096443015319918083[247] = 1.0;
   out_4096443015319918083[248] = 0.0;
   out_4096443015319918083[249] = 0.0;
   out_4096443015319918083[250] = 0.0;
   out_4096443015319918083[251] = 0.0;
   out_4096443015319918083[252] = 0.0;
   out_4096443015319918083[253] = 0.0;
   out_4096443015319918083[254] = 0.0;
   out_4096443015319918083[255] = 0.0;
   out_4096443015319918083[256] = 0.0;
   out_4096443015319918083[257] = 0.0;
   out_4096443015319918083[258] = 0.0;
   out_4096443015319918083[259] = 0.0;
   out_4096443015319918083[260] = 0.0;
   out_4096443015319918083[261] = 0.0;
   out_4096443015319918083[262] = 0.0;
   out_4096443015319918083[263] = 0.0;
   out_4096443015319918083[264] = 0.0;
   out_4096443015319918083[265] = 0.0;
   out_4096443015319918083[266] = 1.0;
   out_4096443015319918083[267] = 0.0;
   out_4096443015319918083[268] = 0.0;
   out_4096443015319918083[269] = 0.0;
   out_4096443015319918083[270] = 0.0;
   out_4096443015319918083[271] = 0.0;
   out_4096443015319918083[272] = 0.0;
   out_4096443015319918083[273] = 0.0;
   out_4096443015319918083[274] = 0.0;
   out_4096443015319918083[275] = 0.0;
   out_4096443015319918083[276] = 0.0;
   out_4096443015319918083[277] = 0.0;
   out_4096443015319918083[278] = 0.0;
   out_4096443015319918083[279] = 0.0;
   out_4096443015319918083[280] = 0.0;
   out_4096443015319918083[281] = 0.0;
   out_4096443015319918083[282] = 0.0;
   out_4096443015319918083[283] = 0.0;
   out_4096443015319918083[284] = 0.0;
   out_4096443015319918083[285] = 1.0;
   out_4096443015319918083[286] = 0.0;
   out_4096443015319918083[287] = 0.0;
   out_4096443015319918083[288] = 0.0;
   out_4096443015319918083[289] = 0.0;
   out_4096443015319918083[290] = 0.0;
   out_4096443015319918083[291] = 0.0;
   out_4096443015319918083[292] = 0.0;
   out_4096443015319918083[293] = 0.0;
   out_4096443015319918083[294] = 0.0;
   out_4096443015319918083[295] = 0.0;
   out_4096443015319918083[296] = 0.0;
   out_4096443015319918083[297] = 0.0;
   out_4096443015319918083[298] = 0.0;
   out_4096443015319918083[299] = 0.0;
   out_4096443015319918083[300] = 0.0;
   out_4096443015319918083[301] = 0.0;
   out_4096443015319918083[302] = 0.0;
   out_4096443015319918083[303] = 0.0;
   out_4096443015319918083[304] = 1.0;
   out_4096443015319918083[305] = 0.0;
   out_4096443015319918083[306] = 0.0;
   out_4096443015319918083[307] = 0.0;
   out_4096443015319918083[308] = 0.0;
   out_4096443015319918083[309] = 0.0;
   out_4096443015319918083[310] = 0.0;
   out_4096443015319918083[311] = 0.0;
   out_4096443015319918083[312] = 0.0;
   out_4096443015319918083[313] = 0.0;
   out_4096443015319918083[314] = 0.0;
   out_4096443015319918083[315] = 0.0;
   out_4096443015319918083[316] = 0.0;
   out_4096443015319918083[317] = 0.0;
   out_4096443015319918083[318] = 0.0;
   out_4096443015319918083[319] = 0.0;
   out_4096443015319918083[320] = 0.0;
   out_4096443015319918083[321] = 0.0;
   out_4096443015319918083[322] = 0.0;
   out_4096443015319918083[323] = 1.0;
}
void f_fun(double *state, double dt, double *out_6359004595403005878) {
   out_6359004595403005878[0] = atan2((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), -(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]));
   out_6359004595403005878[1] = asin(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]));
   out_6359004595403005878[2] = atan2(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), -(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]));
   out_6359004595403005878[3] = dt*state[12] + state[3];
   out_6359004595403005878[4] = dt*state[13] + state[4];
   out_6359004595403005878[5] = dt*state[14] + state[5];
   out_6359004595403005878[6] = state[6];
   out_6359004595403005878[7] = state[7];
   out_6359004595403005878[8] = state[8];
   out_6359004595403005878[9] = state[9];
   out_6359004595403005878[10] = state[10];
   out_6359004595403005878[11] = state[11];
   out_6359004595403005878[12] = state[12];
   out_6359004595403005878[13] = state[13];
   out_6359004595403005878[14] = state[14];
   out_6359004595403005878[15] = state[15];
   out_6359004595403005878[16] = state[16];
   out_6359004595403005878[17] = state[17];
}
void F_fun(double *state, double dt, double *out_6678289125726224618) {
   out_6678289125726224618[0] = ((-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*cos(state[0])*cos(state[1]) - sin(state[0])*cos(dt*state[6])*cos(dt*state[7])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + ((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*cos(state[0])*cos(state[1]) - sin(dt*state[6])*sin(state[0])*cos(dt*state[7])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_6678289125726224618[1] = ((-sin(dt*state[6])*sin(dt*state[8]) - sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*cos(state[1]) - (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*sin(state[1]) - sin(state[1])*cos(dt*state[6])*cos(dt*state[7])*cos(state[0]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*sin(state[1]) + (-sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) + sin(dt*state[8])*cos(dt*state[6]))*cos(state[1]) - sin(dt*state[6])*sin(state[1])*cos(dt*state[7])*cos(state[0]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_6678289125726224618[2] = 0;
   out_6678289125726224618[3] = 0;
   out_6678289125726224618[4] = 0;
   out_6678289125726224618[5] = 0;
   out_6678289125726224618[6] = (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(dt*cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*sin(dt*state[8]) - dt*sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-dt*sin(dt*state[6])*cos(dt*state[8]) + dt*sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) - dt*cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (dt*sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_6678289125726224618[7] = (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[6])*sin(dt*state[7])*cos(state[0])*cos(state[1]) + dt*sin(dt*state[6])*sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) - dt*sin(dt*state[6])*sin(state[1])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[7])*cos(dt*state[6])*cos(state[0])*cos(state[1]) + dt*sin(dt*state[8])*sin(state[0])*cos(dt*state[6])*cos(dt*state[7])*cos(state[1]) - dt*sin(state[1])*cos(dt*state[6])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_6678289125726224618[8] = ((dt*sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + dt*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (dt*sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + ((dt*sin(dt*state[6])*sin(dt*state[8]) + dt*sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*cos(dt*state[8]) + dt*sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_6678289125726224618[9] = 0;
   out_6678289125726224618[10] = 0;
   out_6678289125726224618[11] = 0;
   out_6678289125726224618[12] = 0;
   out_6678289125726224618[13] = 0;
   out_6678289125726224618[14] = 0;
   out_6678289125726224618[15] = 0;
   out_6678289125726224618[16] = 0;
   out_6678289125726224618[17] = 0;
   out_6678289125726224618[18] = (-sin(dt*state[7])*sin(state[0])*cos(state[1]) - sin(dt*state[8])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_6678289125726224618[19] = (-sin(dt*state[7])*sin(state[1])*cos(state[0]) + sin(dt*state[8])*sin(state[0])*sin(state[1])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_6678289125726224618[20] = 0;
   out_6678289125726224618[21] = 0;
   out_6678289125726224618[22] = 0;
   out_6678289125726224618[23] = 0;
   out_6678289125726224618[24] = 0;
   out_6678289125726224618[25] = (dt*sin(dt*state[7])*sin(dt*state[8])*sin(state[0])*cos(state[1]) - dt*sin(dt*state[7])*sin(state[1])*cos(dt*state[8]) + dt*cos(dt*state[7])*cos(state[0])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_6678289125726224618[26] = (-dt*sin(dt*state[8])*sin(state[1])*cos(dt*state[7]) - dt*sin(state[0])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_6678289125726224618[27] = 0;
   out_6678289125726224618[28] = 0;
   out_6678289125726224618[29] = 0;
   out_6678289125726224618[30] = 0;
   out_6678289125726224618[31] = 0;
   out_6678289125726224618[32] = 0;
   out_6678289125726224618[33] = 0;
   out_6678289125726224618[34] = 0;
   out_6678289125726224618[35] = 0;
   out_6678289125726224618[36] = ((sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[7]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[7]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_6678289125726224618[37] = (-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(-sin(dt*state[7])*sin(state[2])*cos(state[0])*cos(state[1]) + sin(dt*state[8])*sin(state[0])*sin(state[2])*cos(dt*state[7])*cos(state[1]) - sin(state[1])*sin(state[2])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*(-sin(dt*state[7])*cos(state[0])*cos(state[1])*cos(state[2]) + sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1])*cos(state[2]) - sin(state[1])*cos(dt*state[7])*cos(dt*state[8])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_6678289125726224618[38] = ((-sin(state[0])*sin(state[2]) - sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (-sin(state[0])*sin(state[1])*sin(state[2]) - cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_6678289125726224618[39] = 0;
   out_6678289125726224618[40] = 0;
   out_6678289125726224618[41] = 0;
   out_6678289125726224618[42] = 0;
   out_6678289125726224618[43] = (-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(dt*(sin(state[0])*cos(state[2]) - sin(state[1])*sin(state[2])*cos(state[0]))*cos(dt*state[7]) - dt*(sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[7])*sin(dt*state[8]) - dt*sin(dt*state[7])*sin(state[2])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*(dt*(-sin(state[0])*sin(state[2]) - sin(state[1])*cos(state[0])*cos(state[2]))*cos(dt*state[7]) - dt*(sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[7])*sin(dt*state[8]) - dt*sin(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_6678289125726224618[44] = (dt*(sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*cos(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*sin(state[2])*cos(dt*state[7])*cos(state[1]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + (dt*(sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*cos(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[7])*cos(state[1])*cos(state[2]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_6678289125726224618[45] = 0;
   out_6678289125726224618[46] = 0;
   out_6678289125726224618[47] = 0;
   out_6678289125726224618[48] = 0;
   out_6678289125726224618[49] = 0;
   out_6678289125726224618[50] = 0;
   out_6678289125726224618[51] = 0;
   out_6678289125726224618[52] = 0;
   out_6678289125726224618[53] = 0;
   out_6678289125726224618[54] = 0;
   out_6678289125726224618[55] = 0;
   out_6678289125726224618[56] = 0;
   out_6678289125726224618[57] = 1;
   out_6678289125726224618[58] = 0;
   out_6678289125726224618[59] = 0;
   out_6678289125726224618[60] = 0;
   out_6678289125726224618[61] = 0;
   out_6678289125726224618[62] = 0;
   out_6678289125726224618[63] = 0;
   out_6678289125726224618[64] = 0;
   out_6678289125726224618[65] = 0;
   out_6678289125726224618[66] = dt;
   out_6678289125726224618[67] = 0;
   out_6678289125726224618[68] = 0;
   out_6678289125726224618[69] = 0;
   out_6678289125726224618[70] = 0;
   out_6678289125726224618[71] = 0;
   out_6678289125726224618[72] = 0;
   out_6678289125726224618[73] = 0;
   out_6678289125726224618[74] = 0;
   out_6678289125726224618[75] = 0;
   out_6678289125726224618[76] = 1;
   out_6678289125726224618[77] = 0;
   out_6678289125726224618[78] = 0;
   out_6678289125726224618[79] = 0;
   out_6678289125726224618[80] = 0;
   out_6678289125726224618[81] = 0;
   out_6678289125726224618[82] = 0;
   out_6678289125726224618[83] = 0;
   out_6678289125726224618[84] = 0;
   out_6678289125726224618[85] = dt;
   out_6678289125726224618[86] = 0;
   out_6678289125726224618[87] = 0;
   out_6678289125726224618[88] = 0;
   out_6678289125726224618[89] = 0;
   out_6678289125726224618[90] = 0;
   out_6678289125726224618[91] = 0;
   out_6678289125726224618[92] = 0;
   out_6678289125726224618[93] = 0;
   out_6678289125726224618[94] = 0;
   out_6678289125726224618[95] = 1;
   out_6678289125726224618[96] = 0;
   out_6678289125726224618[97] = 0;
   out_6678289125726224618[98] = 0;
   out_6678289125726224618[99] = 0;
   out_6678289125726224618[100] = 0;
   out_6678289125726224618[101] = 0;
   out_6678289125726224618[102] = 0;
   out_6678289125726224618[103] = 0;
   out_6678289125726224618[104] = dt;
   out_6678289125726224618[105] = 0;
   out_6678289125726224618[106] = 0;
   out_6678289125726224618[107] = 0;
   out_6678289125726224618[108] = 0;
   out_6678289125726224618[109] = 0;
   out_6678289125726224618[110] = 0;
   out_6678289125726224618[111] = 0;
   out_6678289125726224618[112] = 0;
   out_6678289125726224618[113] = 0;
   out_6678289125726224618[114] = 1;
   out_6678289125726224618[115] = 0;
   out_6678289125726224618[116] = 0;
   out_6678289125726224618[117] = 0;
   out_6678289125726224618[118] = 0;
   out_6678289125726224618[119] = 0;
   out_6678289125726224618[120] = 0;
   out_6678289125726224618[121] = 0;
   out_6678289125726224618[122] = 0;
   out_6678289125726224618[123] = 0;
   out_6678289125726224618[124] = 0;
   out_6678289125726224618[125] = 0;
   out_6678289125726224618[126] = 0;
   out_6678289125726224618[127] = 0;
   out_6678289125726224618[128] = 0;
   out_6678289125726224618[129] = 0;
   out_6678289125726224618[130] = 0;
   out_6678289125726224618[131] = 0;
   out_6678289125726224618[132] = 0;
   out_6678289125726224618[133] = 1;
   out_6678289125726224618[134] = 0;
   out_6678289125726224618[135] = 0;
   out_6678289125726224618[136] = 0;
   out_6678289125726224618[137] = 0;
   out_6678289125726224618[138] = 0;
   out_6678289125726224618[139] = 0;
   out_6678289125726224618[140] = 0;
   out_6678289125726224618[141] = 0;
   out_6678289125726224618[142] = 0;
   out_6678289125726224618[143] = 0;
   out_6678289125726224618[144] = 0;
   out_6678289125726224618[145] = 0;
   out_6678289125726224618[146] = 0;
   out_6678289125726224618[147] = 0;
   out_6678289125726224618[148] = 0;
   out_6678289125726224618[149] = 0;
   out_6678289125726224618[150] = 0;
   out_6678289125726224618[151] = 0;
   out_6678289125726224618[152] = 1;
   out_6678289125726224618[153] = 0;
   out_6678289125726224618[154] = 0;
   out_6678289125726224618[155] = 0;
   out_6678289125726224618[156] = 0;
   out_6678289125726224618[157] = 0;
   out_6678289125726224618[158] = 0;
   out_6678289125726224618[159] = 0;
   out_6678289125726224618[160] = 0;
   out_6678289125726224618[161] = 0;
   out_6678289125726224618[162] = 0;
   out_6678289125726224618[163] = 0;
   out_6678289125726224618[164] = 0;
   out_6678289125726224618[165] = 0;
   out_6678289125726224618[166] = 0;
   out_6678289125726224618[167] = 0;
   out_6678289125726224618[168] = 0;
   out_6678289125726224618[169] = 0;
   out_6678289125726224618[170] = 0;
   out_6678289125726224618[171] = 1;
   out_6678289125726224618[172] = 0;
   out_6678289125726224618[173] = 0;
   out_6678289125726224618[174] = 0;
   out_6678289125726224618[175] = 0;
   out_6678289125726224618[176] = 0;
   out_6678289125726224618[177] = 0;
   out_6678289125726224618[178] = 0;
   out_6678289125726224618[179] = 0;
   out_6678289125726224618[180] = 0;
   out_6678289125726224618[181] = 0;
   out_6678289125726224618[182] = 0;
   out_6678289125726224618[183] = 0;
   out_6678289125726224618[184] = 0;
   out_6678289125726224618[185] = 0;
   out_6678289125726224618[186] = 0;
   out_6678289125726224618[187] = 0;
   out_6678289125726224618[188] = 0;
   out_6678289125726224618[189] = 0;
   out_6678289125726224618[190] = 1;
   out_6678289125726224618[191] = 0;
   out_6678289125726224618[192] = 0;
   out_6678289125726224618[193] = 0;
   out_6678289125726224618[194] = 0;
   out_6678289125726224618[195] = 0;
   out_6678289125726224618[196] = 0;
   out_6678289125726224618[197] = 0;
   out_6678289125726224618[198] = 0;
   out_6678289125726224618[199] = 0;
   out_6678289125726224618[200] = 0;
   out_6678289125726224618[201] = 0;
   out_6678289125726224618[202] = 0;
   out_6678289125726224618[203] = 0;
   out_6678289125726224618[204] = 0;
   out_6678289125726224618[205] = 0;
   out_6678289125726224618[206] = 0;
   out_6678289125726224618[207] = 0;
   out_6678289125726224618[208] = 0;
   out_6678289125726224618[209] = 1;
   out_6678289125726224618[210] = 0;
   out_6678289125726224618[211] = 0;
   out_6678289125726224618[212] = 0;
   out_6678289125726224618[213] = 0;
   out_6678289125726224618[214] = 0;
   out_6678289125726224618[215] = 0;
   out_6678289125726224618[216] = 0;
   out_6678289125726224618[217] = 0;
   out_6678289125726224618[218] = 0;
   out_6678289125726224618[219] = 0;
   out_6678289125726224618[220] = 0;
   out_6678289125726224618[221] = 0;
   out_6678289125726224618[222] = 0;
   out_6678289125726224618[223] = 0;
   out_6678289125726224618[224] = 0;
   out_6678289125726224618[225] = 0;
   out_6678289125726224618[226] = 0;
   out_6678289125726224618[227] = 0;
   out_6678289125726224618[228] = 1;
   out_6678289125726224618[229] = 0;
   out_6678289125726224618[230] = 0;
   out_6678289125726224618[231] = 0;
   out_6678289125726224618[232] = 0;
   out_6678289125726224618[233] = 0;
   out_6678289125726224618[234] = 0;
   out_6678289125726224618[235] = 0;
   out_6678289125726224618[236] = 0;
   out_6678289125726224618[237] = 0;
   out_6678289125726224618[238] = 0;
   out_6678289125726224618[239] = 0;
   out_6678289125726224618[240] = 0;
   out_6678289125726224618[241] = 0;
   out_6678289125726224618[242] = 0;
   out_6678289125726224618[243] = 0;
   out_6678289125726224618[244] = 0;
   out_6678289125726224618[245] = 0;
   out_6678289125726224618[246] = 0;
   out_6678289125726224618[247] = 1;
   out_6678289125726224618[248] = 0;
   out_6678289125726224618[249] = 0;
   out_6678289125726224618[250] = 0;
   out_6678289125726224618[251] = 0;
   out_6678289125726224618[252] = 0;
   out_6678289125726224618[253] = 0;
   out_6678289125726224618[254] = 0;
   out_6678289125726224618[255] = 0;
   out_6678289125726224618[256] = 0;
   out_6678289125726224618[257] = 0;
   out_6678289125726224618[258] = 0;
   out_6678289125726224618[259] = 0;
   out_6678289125726224618[260] = 0;
   out_6678289125726224618[261] = 0;
   out_6678289125726224618[262] = 0;
   out_6678289125726224618[263] = 0;
   out_6678289125726224618[264] = 0;
   out_6678289125726224618[265] = 0;
   out_6678289125726224618[266] = 1;
   out_6678289125726224618[267] = 0;
   out_6678289125726224618[268] = 0;
   out_6678289125726224618[269] = 0;
   out_6678289125726224618[270] = 0;
   out_6678289125726224618[271] = 0;
   out_6678289125726224618[272] = 0;
   out_6678289125726224618[273] = 0;
   out_6678289125726224618[274] = 0;
   out_6678289125726224618[275] = 0;
   out_6678289125726224618[276] = 0;
   out_6678289125726224618[277] = 0;
   out_6678289125726224618[278] = 0;
   out_6678289125726224618[279] = 0;
   out_6678289125726224618[280] = 0;
   out_6678289125726224618[281] = 0;
   out_6678289125726224618[282] = 0;
   out_6678289125726224618[283] = 0;
   out_6678289125726224618[284] = 0;
   out_6678289125726224618[285] = 1;
   out_6678289125726224618[286] = 0;
   out_6678289125726224618[287] = 0;
   out_6678289125726224618[288] = 0;
   out_6678289125726224618[289] = 0;
   out_6678289125726224618[290] = 0;
   out_6678289125726224618[291] = 0;
   out_6678289125726224618[292] = 0;
   out_6678289125726224618[293] = 0;
   out_6678289125726224618[294] = 0;
   out_6678289125726224618[295] = 0;
   out_6678289125726224618[296] = 0;
   out_6678289125726224618[297] = 0;
   out_6678289125726224618[298] = 0;
   out_6678289125726224618[299] = 0;
   out_6678289125726224618[300] = 0;
   out_6678289125726224618[301] = 0;
   out_6678289125726224618[302] = 0;
   out_6678289125726224618[303] = 0;
   out_6678289125726224618[304] = 1;
   out_6678289125726224618[305] = 0;
   out_6678289125726224618[306] = 0;
   out_6678289125726224618[307] = 0;
   out_6678289125726224618[308] = 0;
   out_6678289125726224618[309] = 0;
   out_6678289125726224618[310] = 0;
   out_6678289125726224618[311] = 0;
   out_6678289125726224618[312] = 0;
   out_6678289125726224618[313] = 0;
   out_6678289125726224618[314] = 0;
   out_6678289125726224618[315] = 0;
   out_6678289125726224618[316] = 0;
   out_6678289125726224618[317] = 0;
   out_6678289125726224618[318] = 0;
   out_6678289125726224618[319] = 0;
   out_6678289125726224618[320] = 0;
   out_6678289125726224618[321] = 0;
   out_6678289125726224618[322] = 0;
   out_6678289125726224618[323] = 1;
}
void h_4(double *state, double *unused, double *out_8702070268431109774) {
   out_8702070268431109774[0] = state[6] + state[9];
   out_8702070268431109774[1] = state[7] + state[10];
   out_8702070268431109774[2] = state[8] + state[11];
}
void H_4(double *state, double *unused, double *out_1056075369719162652) {
   out_1056075369719162652[0] = 0;
   out_1056075369719162652[1] = 0;
   out_1056075369719162652[2] = 0;
   out_1056075369719162652[3] = 0;
   out_1056075369719162652[4] = 0;
   out_1056075369719162652[5] = 0;
   out_1056075369719162652[6] = 1;
   out_1056075369719162652[7] = 0;
   out_1056075369719162652[8] = 0;
   out_1056075369719162652[9] = 1;
   out_1056075369719162652[10] = 0;
   out_1056075369719162652[11] = 0;
   out_1056075369719162652[12] = 0;
   out_1056075369719162652[13] = 0;
   out_1056075369719162652[14] = 0;
   out_1056075369719162652[15] = 0;
   out_1056075369719162652[16] = 0;
   out_1056075369719162652[17] = 0;
   out_1056075369719162652[18] = 0;
   out_1056075369719162652[19] = 0;
   out_1056075369719162652[20] = 0;
   out_1056075369719162652[21] = 0;
   out_1056075369719162652[22] = 0;
   out_1056075369719162652[23] = 0;
   out_1056075369719162652[24] = 0;
   out_1056075369719162652[25] = 1;
   out_1056075369719162652[26] = 0;
   out_1056075369719162652[27] = 0;
   out_1056075369719162652[28] = 1;
   out_1056075369719162652[29] = 0;
   out_1056075369719162652[30] = 0;
   out_1056075369719162652[31] = 0;
   out_1056075369719162652[32] = 0;
   out_1056075369719162652[33] = 0;
   out_1056075369719162652[34] = 0;
   out_1056075369719162652[35] = 0;
   out_1056075369719162652[36] = 0;
   out_1056075369719162652[37] = 0;
   out_1056075369719162652[38] = 0;
   out_1056075369719162652[39] = 0;
   out_1056075369719162652[40] = 0;
   out_1056075369719162652[41] = 0;
   out_1056075369719162652[42] = 0;
   out_1056075369719162652[43] = 0;
   out_1056075369719162652[44] = 1;
   out_1056075369719162652[45] = 0;
   out_1056075369719162652[46] = 0;
   out_1056075369719162652[47] = 1;
   out_1056075369719162652[48] = 0;
   out_1056075369719162652[49] = 0;
   out_1056075369719162652[50] = 0;
   out_1056075369719162652[51] = 0;
   out_1056075369719162652[52] = 0;
   out_1056075369719162652[53] = 0;
}
void h_10(double *state, double *unused, double *out_4563905700114918382) {
   out_4563905700114918382[0] = 9.8100000000000005*sin(state[1]) - state[4]*state[8] + state[5]*state[7] + state[12] + state[15];
   out_4563905700114918382[1] = -9.8100000000000005*sin(state[0])*cos(state[1]) + state[3]*state[8] - state[5]*state[6] + state[13] + state[16];
   out_4563905700114918382[2] = -9.8100000000000005*cos(state[0])*cos(state[1]) - state[3]*state[7] + state[4]*state[6] + state[14] + state[17];
}
void H_10(double *state, double *unused, double *out_7730657328515761584) {
   out_7730657328515761584[0] = 0;
   out_7730657328515761584[1] = 9.8100000000000005*cos(state[1]);
   out_7730657328515761584[2] = 0;
   out_7730657328515761584[3] = 0;
   out_7730657328515761584[4] = -state[8];
   out_7730657328515761584[5] = state[7];
   out_7730657328515761584[6] = 0;
   out_7730657328515761584[7] = state[5];
   out_7730657328515761584[8] = -state[4];
   out_7730657328515761584[9] = 0;
   out_7730657328515761584[10] = 0;
   out_7730657328515761584[11] = 0;
   out_7730657328515761584[12] = 1;
   out_7730657328515761584[13] = 0;
   out_7730657328515761584[14] = 0;
   out_7730657328515761584[15] = 1;
   out_7730657328515761584[16] = 0;
   out_7730657328515761584[17] = 0;
   out_7730657328515761584[18] = -9.8100000000000005*cos(state[0])*cos(state[1]);
   out_7730657328515761584[19] = 9.8100000000000005*sin(state[0])*sin(state[1]);
   out_7730657328515761584[20] = 0;
   out_7730657328515761584[21] = state[8];
   out_7730657328515761584[22] = 0;
   out_7730657328515761584[23] = -state[6];
   out_7730657328515761584[24] = -state[5];
   out_7730657328515761584[25] = 0;
   out_7730657328515761584[26] = state[3];
   out_7730657328515761584[27] = 0;
   out_7730657328515761584[28] = 0;
   out_7730657328515761584[29] = 0;
   out_7730657328515761584[30] = 0;
   out_7730657328515761584[31] = 1;
   out_7730657328515761584[32] = 0;
   out_7730657328515761584[33] = 0;
   out_7730657328515761584[34] = 1;
   out_7730657328515761584[35] = 0;
   out_7730657328515761584[36] = 9.8100000000000005*sin(state[0])*cos(state[1]);
   out_7730657328515761584[37] = 9.8100000000000005*sin(state[1])*cos(state[0]);
   out_7730657328515761584[38] = 0;
   out_7730657328515761584[39] = -state[7];
   out_7730657328515761584[40] = state[6];
   out_7730657328515761584[41] = 0;
   out_7730657328515761584[42] = state[4];
   out_7730657328515761584[43] = -state[3];
   out_7730657328515761584[44] = 0;
   out_7730657328515761584[45] = 0;
   out_7730657328515761584[46] = 0;
   out_7730657328515761584[47] = 0;
   out_7730657328515761584[48] = 0;
   out_7730657328515761584[49] = 0;
   out_7730657328515761584[50] = 1;
   out_7730657328515761584[51] = 0;
   out_7730657328515761584[52] = 0;
   out_7730657328515761584[53] = 1;
}
void h_13(double *state, double *unused, double *out_8383994934843595415) {
   out_8383994934843595415[0] = state[3];
   out_8383994934843595415[1] = state[4];
   out_8383994934843595415[2] = state[5];
}
void H_13(double *state, double *unused, double *out_2777680093583361372) {
   out_2777680093583361372[0] = 0;
   out_2777680093583361372[1] = 0;
   out_2777680093583361372[2] = 0;
   out_2777680093583361372[3] = 1;
   out_2777680093583361372[4] = 0;
   out_2777680093583361372[5] = 0;
   out_2777680093583361372[6] = 0;
   out_2777680093583361372[7] = 0;
   out_2777680093583361372[8] = 0;
   out_2777680093583361372[9] = 0;
   out_2777680093583361372[10] = 0;
   out_2777680093583361372[11] = 0;
   out_2777680093583361372[12] = 0;
   out_2777680093583361372[13] = 0;
   out_2777680093583361372[14] = 0;
   out_2777680093583361372[15] = 0;
   out_2777680093583361372[16] = 0;
   out_2777680093583361372[17] = 0;
   out_2777680093583361372[18] = 0;
   out_2777680093583361372[19] = 0;
   out_2777680093583361372[20] = 0;
   out_2777680093583361372[21] = 0;
   out_2777680093583361372[22] = 1;
   out_2777680093583361372[23] = 0;
   out_2777680093583361372[24] = 0;
   out_2777680093583361372[25] = 0;
   out_2777680093583361372[26] = 0;
   out_2777680093583361372[27] = 0;
   out_2777680093583361372[28] = 0;
   out_2777680093583361372[29] = 0;
   out_2777680093583361372[30] = 0;
   out_2777680093583361372[31] = 0;
   out_2777680093583361372[32] = 0;
   out_2777680093583361372[33] = 0;
   out_2777680093583361372[34] = 0;
   out_2777680093583361372[35] = 0;
   out_2777680093583361372[36] = 0;
   out_2777680093583361372[37] = 0;
   out_2777680093583361372[38] = 0;
   out_2777680093583361372[39] = 0;
   out_2777680093583361372[40] = 0;
   out_2777680093583361372[41] = 1;
   out_2777680093583361372[42] = 0;
   out_2777680093583361372[43] = 0;
   out_2777680093583361372[44] = 0;
   out_2777680093583361372[45] = 0;
   out_2777680093583361372[46] = 0;
   out_2777680093583361372[47] = 0;
   out_2777680093583361372[48] = 0;
   out_2777680093583361372[49] = 0;
   out_2777680093583361372[50] = 0;
   out_2777680093583361372[51] = 0;
   out_2777680093583361372[52] = 0;
   out_2777680093583361372[53] = 0;
}
void h_14(double *state, double *unused, double *out_8323654106391695519) {
   out_8323654106391695519[0] = state[6];
   out_8323654106391695519[1] = state[7];
   out_8323654106391695519[2] = state[8];
}
void H_14(double *state, double *unused, double *out_2026713062576209644) {
   out_2026713062576209644[0] = 0;
   out_2026713062576209644[1] = 0;
   out_2026713062576209644[2] = 0;
   out_2026713062576209644[3] = 0;
   out_2026713062576209644[4] = 0;
   out_2026713062576209644[5] = 0;
   out_2026713062576209644[6] = 1;
   out_2026713062576209644[7] = 0;
   out_2026713062576209644[8] = 0;
   out_2026713062576209644[9] = 0;
   out_2026713062576209644[10] = 0;
   out_2026713062576209644[11] = 0;
   out_2026713062576209644[12] = 0;
   out_2026713062576209644[13] = 0;
   out_2026713062576209644[14] = 0;
   out_2026713062576209644[15] = 0;
   out_2026713062576209644[16] = 0;
   out_2026713062576209644[17] = 0;
   out_2026713062576209644[18] = 0;
   out_2026713062576209644[19] = 0;
   out_2026713062576209644[20] = 0;
   out_2026713062576209644[21] = 0;
   out_2026713062576209644[22] = 0;
   out_2026713062576209644[23] = 0;
   out_2026713062576209644[24] = 0;
   out_2026713062576209644[25] = 1;
   out_2026713062576209644[26] = 0;
   out_2026713062576209644[27] = 0;
   out_2026713062576209644[28] = 0;
   out_2026713062576209644[29] = 0;
   out_2026713062576209644[30] = 0;
   out_2026713062576209644[31] = 0;
   out_2026713062576209644[32] = 0;
   out_2026713062576209644[33] = 0;
   out_2026713062576209644[34] = 0;
   out_2026713062576209644[35] = 0;
   out_2026713062576209644[36] = 0;
   out_2026713062576209644[37] = 0;
   out_2026713062576209644[38] = 0;
   out_2026713062576209644[39] = 0;
   out_2026713062576209644[40] = 0;
   out_2026713062576209644[41] = 0;
   out_2026713062576209644[42] = 0;
   out_2026713062576209644[43] = 0;
   out_2026713062576209644[44] = 1;
   out_2026713062576209644[45] = 0;
   out_2026713062576209644[46] = 0;
   out_2026713062576209644[47] = 0;
   out_2026713062576209644[48] = 0;
   out_2026713062576209644[49] = 0;
   out_2026713062576209644[50] = 0;
   out_2026713062576209644[51] = 0;
   out_2026713062576209644[52] = 0;
   out_2026713062576209644[53] = 0;
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
void pose_err_fun(double *nom_x, double *delta_x, double *out_3762875391382386195) {
  err_fun(nom_x, delta_x, out_3762875391382386195);
}
void pose_inv_err_fun(double *nom_x, double *true_x, double *out_1907257459040696591) {
  inv_err_fun(nom_x, true_x, out_1907257459040696591);
}
void pose_H_mod_fun(double *state, double *out_4096443015319918083) {
  H_mod_fun(state, out_4096443015319918083);
}
void pose_f_fun(double *state, double dt, double *out_6359004595403005878) {
  f_fun(state,  dt, out_6359004595403005878);
}
void pose_F_fun(double *state, double dt, double *out_6678289125726224618) {
  F_fun(state,  dt, out_6678289125726224618);
}
void pose_h_4(double *state, double *unused, double *out_8702070268431109774) {
  h_4(state, unused, out_8702070268431109774);
}
void pose_H_4(double *state, double *unused, double *out_1056075369719162652) {
  H_4(state, unused, out_1056075369719162652);
}
void pose_h_10(double *state, double *unused, double *out_4563905700114918382) {
  h_10(state, unused, out_4563905700114918382);
}
void pose_H_10(double *state, double *unused, double *out_7730657328515761584) {
  H_10(state, unused, out_7730657328515761584);
}
void pose_h_13(double *state, double *unused, double *out_8383994934843595415) {
  h_13(state, unused, out_8383994934843595415);
}
void pose_H_13(double *state, double *unused, double *out_2777680093583361372) {
  H_13(state, unused, out_2777680093583361372);
}
void pose_h_14(double *state, double *unused, double *out_8323654106391695519) {
  h_14(state, unused, out_8323654106391695519);
}
void pose_H_14(double *state, double *unused, double *out_2026713062576209644) {
  H_14(state, unused, out_2026713062576209644);
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
