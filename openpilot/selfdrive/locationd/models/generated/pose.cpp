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
void err_fun(double *nom_x, double *delta_x, double *out_8706376808260214389) {
   out_8706376808260214389[0] = delta_x[0] + nom_x[0];
   out_8706376808260214389[1] = delta_x[1] + nom_x[1];
   out_8706376808260214389[2] = delta_x[2] + nom_x[2];
   out_8706376808260214389[3] = delta_x[3] + nom_x[3];
   out_8706376808260214389[4] = delta_x[4] + nom_x[4];
   out_8706376808260214389[5] = delta_x[5] + nom_x[5];
   out_8706376808260214389[6] = delta_x[6] + nom_x[6];
   out_8706376808260214389[7] = delta_x[7] + nom_x[7];
   out_8706376808260214389[8] = delta_x[8] + nom_x[8];
   out_8706376808260214389[9] = delta_x[9] + nom_x[9];
   out_8706376808260214389[10] = delta_x[10] + nom_x[10];
   out_8706376808260214389[11] = delta_x[11] + nom_x[11];
   out_8706376808260214389[12] = delta_x[12] + nom_x[12];
   out_8706376808260214389[13] = delta_x[13] + nom_x[13];
   out_8706376808260214389[14] = delta_x[14] + nom_x[14];
   out_8706376808260214389[15] = delta_x[15] + nom_x[15];
   out_8706376808260214389[16] = delta_x[16] + nom_x[16];
   out_8706376808260214389[17] = delta_x[17] + nom_x[17];
}
void inv_err_fun(double *nom_x, double *true_x, double *out_1316013831039188305) {
   out_1316013831039188305[0] = -nom_x[0] + true_x[0];
   out_1316013831039188305[1] = -nom_x[1] + true_x[1];
   out_1316013831039188305[2] = -nom_x[2] + true_x[2];
   out_1316013831039188305[3] = -nom_x[3] + true_x[3];
   out_1316013831039188305[4] = -nom_x[4] + true_x[4];
   out_1316013831039188305[5] = -nom_x[5] + true_x[5];
   out_1316013831039188305[6] = -nom_x[6] + true_x[6];
   out_1316013831039188305[7] = -nom_x[7] + true_x[7];
   out_1316013831039188305[8] = -nom_x[8] + true_x[8];
   out_1316013831039188305[9] = -nom_x[9] + true_x[9];
   out_1316013831039188305[10] = -nom_x[10] + true_x[10];
   out_1316013831039188305[11] = -nom_x[11] + true_x[11];
   out_1316013831039188305[12] = -nom_x[12] + true_x[12];
   out_1316013831039188305[13] = -nom_x[13] + true_x[13];
   out_1316013831039188305[14] = -nom_x[14] + true_x[14];
   out_1316013831039188305[15] = -nom_x[15] + true_x[15];
   out_1316013831039188305[16] = -nom_x[16] + true_x[16];
   out_1316013831039188305[17] = -nom_x[17] + true_x[17];
}
void H_mod_fun(double *state, double *out_1995820263732979846) {
   out_1995820263732979846[0] = 1.0;
   out_1995820263732979846[1] = 0.0;
   out_1995820263732979846[2] = 0.0;
   out_1995820263732979846[3] = 0.0;
   out_1995820263732979846[4] = 0.0;
   out_1995820263732979846[5] = 0.0;
   out_1995820263732979846[6] = 0.0;
   out_1995820263732979846[7] = 0.0;
   out_1995820263732979846[8] = 0.0;
   out_1995820263732979846[9] = 0.0;
   out_1995820263732979846[10] = 0.0;
   out_1995820263732979846[11] = 0.0;
   out_1995820263732979846[12] = 0.0;
   out_1995820263732979846[13] = 0.0;
   out_1995820263732979846[14] = 0.0;
   out_1995820263732979846[15] = 0.0;
   out_1995820263732979846[16] = 0.0;
   out_1995820263732979846[17] = 0.0;
   out_1995820263732979846[18] = 0.0;
   out_1995820263732979846[19] = 1.0;
   out_1995820263732979846[20] = 0.0;
   out_1995820263732979846[21] = 0.0;
   out_1995820263732979846[22] = 0.0;
   out_1995820263732979846[23] = 0.0;
   out_1995820263732979846[24] = 0.0;
   out_1995820263732979846[25] = 0.0;
   out_1995820263732979846[26] = 0.0;
   out_1995820263732979846[27] = 0.0;
   out_1995820263732979846[28] = 0.0;
   out_1995820263732979846[29] = 0.0;
   out_1995820263732979846[30] = 0.0;
   out_1995820263732979846[31] = 0.0;
   out_1995820263732979846[32] = 0.0;
   out_1995820263732979846[33] = 0.0;
   out_1995820263732979846[34] = 0.0;
   out_1995820263732979846[35] = 0.0;
   out_1995820263732979846[36] = 0.0;
   out_1995820263732979846[37] = 0.0;
   out_1995820263732979846[38] = 1.0;
   out_1995820263732979846[39] = 0.0;
   out_1995820263732979846[40] = 0.0;
   out_1995820263732979846[41] = 0.0;
   out_1995820263732979846[42] = 0.0;
   out_1995820263732979846[43] = 0.0;
   out_1995820263732979846[44] = 0.0;
   out_1995820263732979846[45] = 0.0;
   out_1995820263732979846[46] = 0.0;
   out_1995820263732979846[47] = 0.0;
   out_1995820263732979846[48] = 0.0;
   out_1995820263732979846[49] = 0.0;
   out_1995820263732979846[50] = 0.0;
   out_1995820263732979846[51] = 0.0;
   out_1995820263732979846[52] = 0.0;
   out_1995820263732979846[53] = 0.0;
   out_1995820263732979846[54] = 0.0;
   out_1995820263732979846[55] = 0.0;
   out_1995820263732979846[56] = 0.0;
   out_1995820263732979846[57] = 1.0;
   out_1995820263732979846[58] = 0.0;
   out_1995820263732979846[59] = 0.0;
   out_1995820263732979846[60] = 0.0;
   out_1995820263732979846[61] = 0.0;
   out_1995820263732979846[62] = 0.0;
   out_1995820263732979846[63] = 0.0;
   out_1995820263732979846[64] = 0.0;
   out_1995820263732979846[65] = 0.0;
   out_1995820263732979846[66] = 0.0;
   out_1995820263732979846[67] = 0.0;
   out_1995820263732979846[68] = 0.0;
   out_1995820263732979846[69] = 0.0;
   out_1995820263732979846[70] = 0.0;
   out_1995820263732979846[71] = 0.0;
   out_1995820263732979846[72] = 0.0;
   out_1995820263732979846[73] = 0.0;
   out_1995820263732979846[74] = 0.0;
   out_1995820263732979846[75] = 0.0;
   out_1995820263732979846[76] = 1.0;
   out_1995820263732979846[77] = 0.0;
   out_1995820263732979846[78] = 0.0;
   out_1995820263732979846[79] = 0.0;
   out_1995820263732979846[80] = 0.0;
   out_1995820263732979846[81] = 0.0;
   out_1995820263732979846[82] = 0.0;
   out_1995820263732979846[83] = 0.0;
   out_1995820263732979846[84] = 0.0;
   out_1995820263732979846[85] = 0.0;
   out_1995820263732979846[86] = 0.0;
   out_1995820263732979846[87] = 0.0;
   out_1995820263732979846[88] = 0.0;
   out_1995820263732979846[89] = 0.0;
   out_1995820263732979846[90] = 0.0;
   out_1995820263732979846[91] = 0.0;
   out_1995820263732979846[92] = 0.0;
   out_1995820263732979846[93] = 0.0;
   out_1995820263732979846[94] = 0.0;
   out_1995820263732979846[95] = 1.0;
   out_1995820263732979846[96] = 0.0;
   out_1995820263732979846[97] = 0.0;
   out_1995820263732979846[98] = 0.0;
   out_1995820263732979846[99] = 0.0;
   out_1995820263732979846[100] = 0.0;
   out_1995820263732979846[101] = 0.0;
   out_1995820263732979846[102] = 0.0;
   out_1995820263732979846[103] = 0.0;
   out_1995820263732979846[104] = 0.0;
   out_1995820263732979846[105] = 0.0;
   out_1995820263732979846[106] = 0.0;
   out_1995820263732979846[107] = 0.0;
   out_1995820263732979846[108] = 0.0;
   out_1995820263732979846[109] = 0.0;
   out_1995820263732979846[110] = 0.0;
   out_1995820263732979846[111] = 0.0;
   out_1995820263732979846[112] = 0.0;
   out_1995820263732979846[113] = 0.0;
   out_1995820263732979846[114] = 1.0;
   out_1995820263732979846[115] = 0.0;
   out_1995820263732979846[116] = 0.0;
   out_1995820263732979846[117] = 0.0;
   out_1995820263732979846[118] = 0.0;
   out_1995820263732979846[119] = 0.0;
   out_1995820263732979846[120] = 0.0;
   out_1995820263732979846[121] = 0.0;
   out_1995820263732979846[122] = 0.0;
   out_1995820263732979846[123] = 0.0;
   out_1995820263732979846[124] = 0.0;
   out_1995820263732979846[125] = 0.0;
   out_1995820263732979846[126] = 0.0;
   out_1995820263732979846[127] = 0.0;
   out_1995820263732979846[128] = 0.0;
   out_1995820263732979846[129] = 0.0;
   out_1995820263732979846[130] = 0.0;
   out_1995820263732979846[131] = 0.0;
   out_1995820263732979846[132] = 0.0;
   out_1995820263732979846[133] = 1.0;
   out_1995820263732979846[134] = 0.0;
   out_1995820263732979846[135] = 0.0;
   out_1995820263732979846[136] = 0.0;
   out_1995820263732979846[137] = 0.0;
   out_1995820263732979846[138] = 0.0;
   out_1995820263732979846[139] = 0.0;
   out_1995820263732979846[140] = 0.0;
   out_1995820263732979846[141] = 0.0;
   out_1995820263732979846[142] = 0.0;
   out_1995820263732979846[143] = 0.0;
   out_1995820263732979846[144] = 0.0;
   out_1995820263732979846[145] = 0.0;
   out_1995820263732979846[146] = 0.0;
   out_1995820263732979846[147] = 0.0;
   out_1995820263732979846[148] = 0.0;
   out_1995820263732979846[149] = 0.0;
   out_1995820263732979846[150] = 0.0;
   out_1995820263732979846[151] = 0.0;
   out_1995820263732979846[152] = 1.0;
   out_1995820263732979846[153] = 0.0;
   out_1995820263732979846[154] = 0.0;
   out_1995820263732979846[155] = 0.0;
   out_1995820263732979846[156] = 0.0;
   out_1995820263732979846[157] = 0.0;
   out_1995820263732979846[158] = 0.0;
   out_1995820263732979846[159] = 0.0;
   out_1995820263732979846[160] = 0.0;
   out_1995820263732979846[161] = 0.0;
   out_1995820263732979846[162] = 0.0;
   out_1995820263732979846[163] = 0.0;
   out_1995820263732979846[164] = 0.0;
   out_1995820263732979846[165] = 0.0;
   out_1995820263732979846[166] = 0.0;
   out_1995820263732979846[167] = 0.0;
   out_1995820263732979846[168] = 0.0;
   out_1995820263732979846[169] = 0.0;
   out_1995820263732979846[170] = 0.0;
   out_1995820263732979846[171] = 1.0;
   out_1995820263732979846[172] = 0.0;
   out_1995820263732979846[173] = 0.0;
   out_1995820263732979846[174] = 0.0;
   out_1995820263732979846[175] = 0.0;
   out_1995820263732979846[176] = 0.0;
   out_1995820263732979846[177] = 0.0;
   out_1995820263732979846[178] = 0.0;
   out_1995820263732979846[179] = 0.0;
   out_1995820263732979846[180] = 0.0;
   out_1995820263732979846[181] = 0.0;
   out_1995820263732979846[182] = 0.0;
   out_1995820263732979846[183] = 0.0;
   out_1995820263732979846[184] = 0.0;
   out_1995820263732979846[185] = 0.0;
   out_1995820263732979846[186] = 0.0;
   out_1995820263732979846[187] = 0.0;
   out_1995820263732979846[188] = 0.0;
   out_1995820263732979846[189] = 0.0;
   out_1995820263732979846[190] = 1.0;
   out_1995820263732979846[191] = 0.0;
   out_1995820263732979846[192] = 0.0;
   out_1995820263732979846[193] = 0.0;
   out_1995820263732979846[194] = 0.0;
   out_1995820263732979846[195] = 0.0;
   out_1995820263732979846[196] = 0.0;
   out_1995820263732979846[197] = 0.0;
   out_1995820263732979846[198] = 0.0;
   out_1995820263732979846[199] = 0.0;
   out_1995820263732979846[200] = 0.0;
   out_1995820263732979846[201] = 0.0;
   out_1995820263732979846[202] = 0.0;
   out_1995820263732979846[203] = 0.0;
   out_1995820263732979846[204] = 0.0;
   out_1995820263732979846[205] = 0.0;
   out_1995820263732979846[206] = 0.0;
   out_1995820263732979846[207] = 0.0;
   out_1995820263732979846[208] = 0.0;
   out_1995820263732979846[209] = 1.0;
   out_1995820263732979846[210] = 0.0;
   out_1995820263732979846[211] = 0.0;
   out_1995820263732979846[212] = 0.0;
   out_1995820263732979846[213] = 0.0;
   out_1995820263732979846[214] = 0.0;
   out_1995820263732979846[215] = 0.0;
   out_1995820263732979846[216] = 0.0;
   out_1995820263732979846[217] = 0.0;
   out_1995820263732979846[218] = 0.0;
   out_1995820263732979846[219] = 0.0;
   out_1995820263732979846[220] = 0.0;
   out_1995820263732979846[221] = 0.0;
   out_1995820263732979846[222] = 0.0;
   out_1995820263732979846[223] = 0.0;
   out_1995820263732979846[224] = 0.0;
   out_1995820263732979846[225] = 0.0;
   out_1995820263732979846[226] = 0.0;
   out_1995820263732979846[227] = 0.0;
   out_1995820263732979846[228] = 1.0;
   out_1995820263732979846[229] = 0.0;
   out_1995820263732979846[230] = 0.0;
   out_1995820263732979846[231] = 0.0;
   out_1995820263732979846[232] = 0.0;
   out_1995820263732979846[233] = 0.0;
   out_1995820263732979846[234] = 0.0;
   out_1995820263732979846[235] = 0.0;
   out_1995820263732979846[236] = 0.0;
   out_1995820263732979846[237] = 0.0;
   out_1995820263732979846[238] = 0.0;
   out_1995820263732979846[239] = 0.0;
   out_1995820263732979846[240] = 0.0;
   out_1995820263732979846[241] = 0.0;
   out_1995820263732979846[242] = 0.0;
   out_1995820263732979846[243] = 0.0;
   out_1995820263732979846[244] = 0.0;
   out_1995820263732979846[245] = 0.0;
   out_1995820263732979846[246] = 0.0;
   out_1995820263732979846[247] = 1.0;
   out_1995820263732979846[248] = 0.0;
   out_1995820263732979846[249] = 0.0;
   out_1995820263732979846[250] = 0.0;
   out_1995820263732979846[251] = 0.0;
   out_1995820263732979846[252] = 0.0;
   out_1995820263732979846[253] = 0.0;
   out_1995820263732979846[254] = 0.0;
   out_1995820263732979846[255] = 0.0;
   out_1995820263732979846[256] = 0.0;
   out_1995820263732979846[257] = 0.0;
   out_1995820263732979846[258] = 0.0;
   out_1995820263732979846[259] = 0.0;
   out_1995820263732979846[260] = 0.0;
   out_1995820263732979846[261] = 0.0;
   out_1995820263732979846[262] = 0.0;
   out_1995820263732979846[263] = 0.0;
   out_1995820263732979846[264] = 0.0;
   out_1995820263732979846[265] = 0.0;
   out_1995820263732979846[266] = 1.0;
   out_1995820263732979846[267] = 0.0;
   out_1995820263732979846[268] = 0.0;
   out_1995820263732979846[269] = 0.0;
   out_1995820263732979846[270] = 0.0;
   out_1995820263732979846[271] = 0.0;
   out_1995820263732979846[272] = 0.0;
   out_1995820263732979846[273] = 0.0;
   out_1995820263732979846[274] = 0.0;
   out_1995820263732979846[275] = 0.0;
   out_1995820263732979846[276] = 0.0;
   out_1995820263732979846[277] = 0.0;
   out_1995820263732979846[278] = 0.0;
   out_1995820263732979846[279] = 0.0;
   out_1995820263732979846[280] = 0.0;
   out_1995820263732979846[281] = 0.0;
   out_1995820263732979846[282] = 0.0;
   out_1995820263732979846[283] = 0.0;
   out_1995820263732979846[284] = 0.0;
   out_1995820263732979846[285] = 1.0;
   out_1995820263732979846[286] = 0.0;
   out_1995820263732979846[287] = 0.0;
   out_1995820263732979846[288] = 0.0;
   out_1995820263732979846[289] = 0.0;
   out_1995820263732979846[290] = 0.0;
   out_1995820263732979846[291] = 0.0;
   out_1995820263732979846[292] = 0.0;
   out_1995820263732979846[293] = 0.0;
   out_1995820263732979846[294] = 0.0;
   out_1995820263732979846[295] = 0.0;
   out_1995820263732979846[296] = 0.0;
   out_1995820263732979846[297] = 0.0;
   out_1995820263732979846[298] = 0.0;
   out_1995820263732979846[299] = 0.0;
   out_1995820263732979846[300] = 0.0;
   out_1995820263732979846[301] = 0.0;
   out_1995820263732979846[302] = 0.0;
   out_1995820263732979846[303] = 0.0;
   out_1995820263732979846[304] = 1.0;
   out_1995820263732979846[305] = 0.0;
   out_1995820263732979846[306] = 0.0;
   out_1995820263732979846[307] = 0.0;
   out_1995820263732979846[308] = 0.0;
   out_1995820263732979846[309] = 0.0;
   out_1995820263732979846[310] = 0.0;
   out_1995820263732979846[311] = 0.0;
   out_1995820263732979846[312] = 0.0;
   out_1995820263732979846[313] = 0.0;
   out_1995820263732979846[314] = 0.0;
   out_1995820263732979846[315] = 0.0;
   out_1995820263732979846[316] = 0.0;
   out_1995820263732979846[317] = 0.0;
   out_1995820263732979846[318] = 0.0;
   out_1995820263732979846[319] = 0.0;
   out_1995820263732979846[320] = 0.0;
   out_1995820263732979846[321] = 0.0;
   out_1995820263732979846[322] = 0.0;
   out_1995820263732979846[323] = 1.0;
}
void f_fun(double *state, double dt, double *out_1989172059616365876) {
   out_1989172059616365876[0] = atan2((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), -(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]));
   out_1989172059616365876[1] = asin(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]));
   out_1989172059616365876[2] = atan2(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), -(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]));
   out_1989172059616365876[3] = dt*state[12] + state[3];
   out_1989172059616365876[4] = dt*state[13] + state[4];
   out_1989172059616365876[5] = dt*state[14] + state[5];
   out_1989172059616365876[6] = state[6];
   out_1989172059616365876[7] = state[7];
   out_1989172059616365876[8] = state[8];
   out_1989172059616365876[9] = state[9];
   out_1989172059616365876[10] = state[10];
   out_1989172059616365876[11] = state[11];
   out_1989172059616365876[12] = state[12];
   out_1989172059616365876[13] = state[13];
   out_1989172059616365876[14] = state[14];
   out_1989172059616365876[15] = state[15];
   out_1989172059616365876[16] = state[16];
   out_1989172059616365876[17] = state[17];
}
void F_fun(double *state, double dt, double *out_1876162241026325508) {
   out_1876162241026325508[0] = ((-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*cos(state[0])*cos(state[1]) - sin(state[0])*cos(dt*state[6])*cos(dt*state[7])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + ((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*cos(state[0])*cos(state[1]) - sin(dt*state[6])*sin(state[0])*cos(dt*state[7])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_1876162241026325508[1] = ((-sin(dt*state[6])*sin(dt*state[8]) - sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*cos(state[1]) - (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*sin(state[1]) - sin(state[1])*cos(dt*state[6])*cos(dt*state[7])*cos(state[0]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*sin(state[1]) + (-sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) + sin(dt*state[8])*cos(dt*state[6]))*cos(state[1]) - sin(dt*state[6])*sin(state[1])*cos(dt*state[7])*cos(state[0]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_1876162241026325508[2] = 0;
   out_1876162241026325508[3] = 0;
   out_1876162241026325508[4] = 0;
   out_1876162241026325508[5] = 0;
   out_1876162241026325508[6] = (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(dt*cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*sin(dt*state[8]) - dt*sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-dt*sin(dt*state[6])*cos(dt*state[8]) + dt*sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) - dt*cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (dt*sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_1876162241026325508[7] = (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[6])*sin(dt*state[7])*cos(state[0])*cos(state[1]) + dt*sin(dt*state[6])*sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) - dt*sin(dt*state[6])*sin(state[1])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[7])*cos(dt*state[6])*cos(state[0])*cos(state[1]) + dt*sin(dt*state[8])*sin(state[0])*cos(dt*state[6])*cos(dt*state[7])*cos(state[1]) - dt*sin(state[1])*cos(dt*state[6])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_1876162241026325508[8] = ((dt*sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + dt*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (dt*sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + ((dt*sin(dt*state[6])*sin(dt*state[8]) + dt*sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*cos(dt*state[8]) + dt*sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_1876162241026325508[9] = 0;
   out_1876162241026325508[10] = 0;
   out_1876162241026325508[11] = 0;
   out_1876162241026325508[12] = 0;
   out_1876162241026325508[13] = 0;
   out_1876162241026325508[14] = 0;
   out_1876162241026325508[15] = 0;
   out_1876162241026325508[16] = 0;
   out_1876162241026325508[17] = 0;
   out_1876162241026325508[18] = (-sin(dt*state[7])*sin(state[0])*cos(state[1]) - sin(dt*state[8])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_1876162241026325508[19] = (-sin(dt*state[7])*sin(state[1])*cos(state[0]) + sin(dt*state[8])*sin(state[0])*sin(state[1])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_1876162241026325508[20] = 0;
   out_1876162241026325508[21] = 0;
   out_1876162241026325508[22] = 0;
   out_1876162241026325508[23] = 0;
   out_1876162241026325508[24] = 0;
   out_1876162241026325508[25] = (dt*sin(dt*state[7])*sin(dt*state[8])*sin(state[0])*cos(state[1]) - dt*sin(dt*state[7])*sin(state[1])*cos(dt*state[8]) + dt*cos(dt*state[7])*cos(state[0])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_1876162241026325508[26] = (-dt*sin(dt*state[8])*sin(state[1])*cos(dt*state[7]) - dt*sin(state[0])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_1876162241026325508[27] = 0;
   out_1876162241026325508[28] = 0;
   out_1876162241026325508[29] = 0;
   out_1876162241026325508[30] = 0;
   out_1876162241026325508[31] = 0;
   out_1876162241026325508[32] = 0;
   out_1876162241026325508[33] = 0;
   out_1876162241026325508[34] = 0;
   out_1876162241026325508[35] = 0;
   out_1876162241026325508[36] = ((sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[7]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[7]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_1876162241026325508[37] = (-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(-sin(dt*state[7])*sin(state[2])*cos(state[0])*cos(state[1]) + sin(dt*state[8])*sin(state[0])*sin(state[2])*cos(dt*state[7])*cos(state[1]) - sin(state[1])*sin(state[2])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*(-sin(dt*state[7])*cos(state[0])*cos(state[1])*cos(state[2]) + sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1])*cos(state[2]) - sin(state[1])*cos(dt*state[7])*cos(dt*state[8])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_1876162241026325508[38] = ((-sin(state[0])*sin(state[2]) - sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (-sin(state[0])*sin(state[1])*sin(state[2]) - cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_1876162241026325508[39] = 0;
   out_1876162241026325508[40] = 0;
   out_1876162241026325508[41] = 0;
   out_1876162241026325508[42] = 0;
   out_1876162241026325508[43] = (-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(dt*(sin(state[0])*cos(state[2]) - sin(state[1])*sin(state[2])*cos(state[0]))*cos(dt*state[7]) - dt*(sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[7])*sin(dt*state[8]) - dt*sin(dt*state[7])*sin(state[2])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*(dt*(-sin(state[0])*sin(state[2]) - sin(state[1])*cos(state[0])*cos(state[2]))*cos(dt*state[7]) - dt*(sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[7])*sin(dt*state[8]) - dt*sin(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_1876162241026325508[44] = (dt*(sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*cos(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*sin(state[2])*cos(dt*state[7])*cos(state[1]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + (dt*(sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*cos(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[7])*cos(state[1])*cos(state[2]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_1876162241026325508[45] = 0;
   out_1876162241026325508[46] = 0;
   out_1876162241026325508[47] = 0;
   out_1876162241026325508[48] = 0;
   out_1876162241026325508[49] = 0;
   out_1876162241026325508[50] = 0;
   out_1876162241026325508[51] = 0;
   out_1876162241026325508[52] = 0;
   out_1876162241026325508[53] = 0;
   out_1876162241026325508[54] = 0;
   out_1876162241026325508[55] = 0;
   out_1876162241026325508[56] = 0;
   out_1876162241026325508[57] = 1;
   out_1876162241026325508[58] = 0;
   out_1876162241026325508[59] = 0;
   out_1876162241026325508[60] = 0;
   out_1876162241026325508[61] = 0;
   out_1876162241026325508[62] = 0;
   out_1876162241026325508[63] = 0;
   out_1876162241026325508[64] = 0;
   out_1876162241026325508[65] = 0;
   out_1876162241026325508[66] = dt;
   out_1876162241026325508[67] = 0;
   out_1876162241026325508[68] = 0;
   out_1876162241026325508[69] = 0;
   out_1876162241026325508[70] = 0;
   out_1876162241026325508[71] = 0;
   out_1876162241026325508[72] = 0;
   out_1876162241026325508[73] = 0;
   out_1876162241026325508[74] = 0;
   out_1876162241026325508[75] = 0;
   out_1876162241026325508[76] = 1;
   out_1876162241026325508[77] = 0;
   out_1876162241026325508[78] = 0;
   out_1876162241026325508[79] = 0;
   out_1876162241026325508[80] = 0;
   out_1876162241026325508[81] = 0;
   out_1876162241026325508[82] = 0;
   out_1876162241026325508[83] = 0;
   out_1876162241026325508[84] = 0;
   out_1876162241026325508[85] = dt;
   out_1876162241026325508[86] = 0;
   out_1876162241026325508[87] = 0;
   out_1876162241026325508[88] = 0;
   out_1876162241026325508[89] = 0;
   out_1876162241026325508[90] = 0;
   out_1876162241026325508[91] = 0;
   out_1876162241026325508[92] = 0;
   out_1876162241026325508[93] = 0;
   out_1876162241026325508[94] = 0;
   out_1876162241026325508[95] = 1;
   out_1876162241026325508[96] = 0;
   out_1876162241026325508[97] = 0;
   out_1876162241026325508[98] = 0;
   out_1876162241026325508[99] = 0;
   out_1876162241026325508[100] = 0;
   out_1876162241026325508[101] = 0;
   out_1876162241026325508[102] = 0;
   out_1876162241026325508[103] = 0;
   out_1876162241026325508[104] = dt;
   out_1876162241026325508[105] = 0;
   out_1876162241026325508[106] = 0;
   out_1876162241026325508[107] = 0;
   out_1876162241026325508[108] = 0;
   out_1876162241026325508[109] = 0;
   out_1876162241026325508[110] = 0;
   out_1876162241026325508[111] = 0;
   out_1876162241026325508[112] = 0;
   out_1876162241026325508[113] = 0;
   out_1876162241026325508[114] = 1;
   out_1876162241026325508[115] = 0;
   out_1876162241026325508[116] = 0;
   out_1876162241026325508[117] = 0;
   out_1876162241026325508[118] = 0;
   out_1876162241026325508[119] = 0;
   out_1876162241026325508[120] = 0;
   out_1876162241026325508[121] = 0;
   out_1876162241026325508[122] = 0;
   out_1876162241026325508[123] = 0;
   out_1876162241026325508[124] = 0;
   out_1876162241026325508[125] = 0;
   out_1876162241026325508[126] = 0;
   out_1876162241026325508[127] = 0;
   out_1876162241026325508[128] = 0;
   out_1876162241026325508[129] = 0;
   out_1876162241026325508[130] = 0;
   out_1876162241026325508[131] = 0;
   out_1876162241026325508[132] = 0;
   out_1876162241026325508[133] = 1;
   out_1876162241026325508[134] = 0;
   out_1876162241026325508[135] = 0;
   out_1876162241026325508[136] = 0;
   out_1876162241026325508[137] = 0;
   out_1876162241026325508[138] = 0;
   out_1876162241026325508[139] = 0;
   out_1876162241026325508[140] = 0;
   out_1876162241026325508[141] = 0;
   out_1876162241026325508[142] = 0;
   out_1876162241026325508[143] = 0;
   out_1876162241026325508[144] = 0;
   out_1876162241026325508[145] = 0;
   out_1876162241026325508[146] = 0;
   out_1876162241026325508[147] = 0;
   out_1876162241026325508[148] = 0;
   out_1876162241026325508[149] = 0;
   out_1876162241026325508[150] = 0;
   out_1876162241026325508[151] = 0;
   out_1876162241026325508[152] = 1;
   out_1876162241026325508[153] = 0;
   out_1876162241026325508[154] = 0;
   out_1876162241026325508[155] = 0;
   out_1876162241026325508[156] = 0;
   out_1876162241026325508[157] = 0;
   out_1876162241026325508[158] = 0;
   out_1876162241026325508[159] = 0;
   out_1876162241026325508[160] = 0;
   out_1876162241026325508[161] = 0;
   out_1876162241026325508[162] = 0;
   out_1876162241026325508[163] = 0;
   out_1876162241026325508[164] = 0;
   out_1876162241026325508[165] = 0;
   out_1876162241026325508[166] = 0;
   out_1876162241026325508[167] = 0;
   out_1876162241026325508[168] = 0;
   out_1876162241026325508[169] = 0;
   out_1876162241026325508[170] = 0;
   out_1876162241026325508[171] = 1;
   out_1876162241026325508[172] = 0;
   out_1876162241026325508[173] = 0;
   out_1876162241026325508[174] = 0;
   out_1876162241026325508[175] = 0;
   out_1876162241026325508[176] = 0;
   out_1876162241026325508[177] = 0;
   out_1876162241026325508[178] = 0;
   out_1876162241026325508[179] = 0;
   out_1876162241026325508[180] = 0;
   out_1876162241026325508[181] = 0;
   out_1876162241026325508[182] = 0;
   out_1876162241026325508[183] = 0;
   out_1876162241026325508[184] = 0;
   out_1876162241026325508[185] = 0;
   out_1876162241026325508[186] = 0;
   out_1876162241026325508[187] = 0;
   out_1876162241026325508[188] = 0;
   out_1876162241026325508[189] = 0;
   out_1876162241026325508[190] = 1;
   out_1876162241026325508[191] = 0;
   out_1876162241026325508[192] = 0;
   out_1876162241026325508[193] = 0;
   out_1876162241026325508[194] = 0;
   out_1876162241026325508[195] = 0;
   out_1876162241026325508[196] = 0;
   out_1876162241026325508[197] = 0;
   out_1876162241026325508[198] = 0;
   out_1876162241026325508[199] = 0;
   out_1876162241026325508[200] = 0;
   out_1876162241026325508[201] = 0;
   out_1876162241026325508[202] = 0;
   out_1876162241026325508[203] = 0;
   out_1876162241026325508[204] = 0;
   out_1876162241026325508[205] = 0;
   out_1876162241026325508[206] = 0;
   out_1876162241026325508[207] = 0;
   out_1876162241026325508[208] = 0;
   out_1876162241026325508[209] = 1;
   out_1876162241026325508[210] = 0;
   out_1876162241026325508[211] = 0;
   out_1876162241026325508[212] = 0;
   out_1876162241026325508[213] = 0;
   out_1876162241026325508[214] = 0;
   out_1876162241026325508[215] = 0;
   out_1876162241026325508[216] = 0;
   out_1876162241026325508[217] = 0;
   out_1876162241026325508[218] = 0;
   out_1876162241026325508[219] = 0;
   out_1876162241026325508[220] = 0;
   out_1876162241026325508[221] = 0;
   out_1876162241026325508[222] = 0;
   out_1876162241026325508[223] = 0;
   out_1876162241026325508[224] = 0;
   out_1876162241026325508[225] = 0;
   out_1876162241026325508[226] = 0;
   out_1876162241026325508[227] = 0;
   out_1876162241026325508[228] = 1;
   out_1876162241026325508[229] = 0;
   out_1876162241026325508[230] = 0;
   out_1876162241026325508[231] = 0;
   out_1876162241026325508[232] = 0;
   out_1876162241026325508[233] = 0;
   out_1876162241026325508[234] = 0;
   out_1876162241026325508[235] = 0;
   out_1876162241026325508[236] = 0;
   out_1876162241026325508[237] = 0;
   out_1876162241026325508[238] = 0;
   out_1876162241026325508[239] = 0;
   out_1876162241026325508[240] = 0;
   out_1876162241026325508[241] = 0;
   out_1876162241026325508[242] = 0;
   out_1876162241026325508[243] = 0;
   out_1876162241026325508[244] = 0;
   out_1876162241026325508[245] = 0;
   out_1876162241026325508[246] = 0;
   out_1876162241026325508[247] = 1;
   out_1876162241026325508[248] = 0;
   out_1876162241026325508[249] = 0;
   out_1876162241026325508[250] = 0;
   out_1876162241026325508[251] = 0;
   out_1876162241026325508[252] = 0;
   out_1876162241026325508[253] = 0;
   out_1876162241026325508[254] = 0;
   out_1876162241026325508[255] = 0;
   out_1876162241026325508[256] = 0;
   out_1876162241026325508[257] = 0;
   out_1876162241026325508[258] = 0;
   out_1876162241026325508[259] = 0;
   out_1876162241026325508[260] = 0;
   out_1876162241026325508[261] = 0;
   out_1876162241026325508[262] = 0;
   out_1876162241026325508[263] = 0;
   out_1876162241026325508[264] = 0;
   out_1876162241026325508[265] = 0;
   out_1876162241026325508[266] = 1;
   out_1876162241026325508[267] = 0;
   out_1876162241026325508[268] = 0;
   out_1876162241026325508[269] = 0;
   out_1876162241026325508[270] = 0;
   out_1876162241026325508[271] = 0;
   out_1876162241026325508[272] = 0;
   out_1876162241026325508[273] = 0;
   out_1876162241026325508[274] = 0;
   out_1876162241026325508[275] = 0;
   out_1876162241026325508[276] = 0;
   out_1876162241026325508[277] = 0;
   out_1876162241026325508[278] = 0;
   out_1876162241026325508[279] = 0;
   out_1876162241026325508[280] = 0;
   out_1876162241026325508[281] = 0;
   out_1876162241026325508[282] = 0;
   out_1876162241026325508[283] = 0;
   out_1876162241026325508[284] = 0;
   out_1876162241026325508[285] = 1;
   out_1876162241026325508[286] = 0;
   out_1876162241026325508[287] = 0;
   out_1876162241026325508[288] = 0;
   out_1876162241026325508[289] = 0;
   out_1876162241026325508[290] = 0;
   out_1876162241026325508[291] = 0;
   out_1876162241026325508[292] = 0;
   out_1876162241026325508[293] = 0;
   out_1876162241026325508[294] = 0;
   out_1876162241026325508[295] = 0;
   out_1876162241026325508[296] = 0;
   out_1876162241026325508[297] = 0;
   out_1876162241026325508[298] = 0;
   out_1876162241026325508[299] = 0;
   out_1876162241026325508[300] = 0;
   out_1876162241026325508[301] = 0;
   out_1876162241026325508[302] = 0;
   out_1876162241026325508[303] = 0;
   out_1876162241026325508[304] = 1;
   out_1876162241026325508[305] = 0;
   out_1876162241026325508[306] = 0;
   out_1876162241026325508[307] = 0;
   out_1876162241026325508[308] = 0;
   out_1876162241026325508[309] = 0;
   out_1876162241026325508[310] = 0;
   out_1876162241026325508[311] = 0;
   out_1876162241026325508[312] = 0;
   out_1876162241026325508[313] = 0;
   out_1876162241026325508[314] = 0;
   out_1876162241026325508[315] = 0;
   out_1876162241026325508[316] = 0;
   out_1876162241026325508[317] = 0;
   out_1876162241026325508[318] = 0;
   out_1876162241026325508[319] = 0;
   out_1876162241026325508[320] = 0;
   out_1876162241026325508[321] = 0;
   out_1876162241026325508[322] = 0;
   out_1876162241026325508[323] = 1;
}
void h_4(double *state, double *unused, double *out_8913681603248625200) {
   out_8913681603248625200[0] = state[6] + state[9];
   out_8913681603248625200[1] = state[7] + state[10];
   out_8913681603248625200[2] = state[8] + state[11];
}
void H_4(double *state, double *unused, double *out_7148338648772060581) {
   out_7148338648772060581[0] = 0;
   out_7148338648772060581[1] = 0;
   out_7148338648772060581[2] = 0;
   out_7148338648772060581[3] = 0;
   out_7148338648772060581[4] = 0;
   out_7148338648772060581[5] = 0;
   out_7148338648772060581[6] = 1;
   out_7148338648772060581[7] = 0;
   out_7148338648772060581[8] = 0;
   out_7148338648772060581[9] = 1;
   out_7148338648772060581[10] = 0;
   out_7148338648772060581[11] = 0;
   out_7148338648772060581[12] = 0;
   out_7148338648772060581[13] = 0;
   out_7148338648772060581[14] = 0;
   out_7148338648772060581[15] = 0;
   out_7148338648772060581[16] = 0;
   out_7148338648772060581[17] = 0;
   out_7148338648772060581[18] = 0;
   out_7148338648772060581[19] = 0;
   out_7148338648772060581[20] = 0;
   out_7148338648772060581[21] = 0;
   out_7148338648772060581[22] = 0;
   out_7148338648772060581[23] = 0;
   out_7148338648772060581[24] = 0;
   out_7148338648772060581[25] = 1;
   out_7148338648772060581[26] = 0;
   out_7148338648772060581[27] = 0;
   out_7148338648772060581[28] = 1;
   out_7148338648772060581[29] = 0;
   out_7148338648772060581[30] = 0;
   out_7148338648772060581[31] = 0;
   out_7148338648772060581[32] = 0;
   out_7148338648772060581[33] = 0;
   out_7148338648772060581[34] = 0;
   out_7148338648772060581[35] = 0;
   out_7148338648772060581[36] = 0;
   out_7148338648772060581[37] = 0;
   out_7148338648772060581[38] = 0;
   out_7148338648772060581[39] = 0;
   out_7148338648772060581[40] = 0;
   out_7148338648772060581[41] = 0;
   out_7148338648772060581[42] = 0;
   out_7148338648772060581[43] = 0;
   out_7148338648772060581[44] = 1;
   out_7148338648772060581[45] = 0;
   out_7148338648772060581[46] = 0;
   out_7148338648772060581[47] = 1;
   out_7148338648772060581[48] = 0;
   out_7148338648772060581[49] = 0;
   out_7148338648772060581[50] = 0;
   out_7148338648772060581[51] = 0;
   out_7148338648772060581[52] = 0;
   out_7148338648772060581[53] = 0;
}
void h_10(double *state, double *unused, double *out_5957325102648707682) {
   out_5957325102648707682[0] = 9.8100000000000005*sin(state[1]) - state[4]*state[8] + state[5]*state[7] + state[12] + state[15];
   out_5957325102648707682[1] = -9.8100000000000005*sin(state[0])*cos(state[1]) + state[3]*state[8] - state[5]*state[6] + state[13] + state[16];
   out_5957325102648707682[2] = -9.8100000000000005*cos(state[0])*cos(state[1]) - state[3]*state[7] + state[4]*state[6] + state[14] + state[17];
}
void H_10(double *state, double *unused, double *out_8659941392114727724) {
   out_8659941392114727724[0] = 0;
   out_8659941392114727724[1] = 9.8100000000000005*cos(state[1]);
   out_8659941392114727724[2] = 0;
   out_8659941392114727724[3] = 0;
   out_8659941392114727724[4] = -state[8];
   out_8659941392114727724[5] = state[7];
   out_8659941392114727724[6] = 0;
   out_8659941392114727724[7] = state[5];
   out_8659941392114727724[8] = -state[4];
   out_8659941392114727724[9] = 0;
   out_8659941392114727724[10] = 0;
   out_8659941392114727724[11] = 0;
   out_8659941392114727724[12] = 1;
   out_8659941392114727724[13] = 0;
   out_8659941392114727724[14] = 0;
   out_8659941392114727724[15] = 1;
   out_8659941392114727724[16] = 0;
   out_8659941392114727724[17] = 0;
   out_8659941392114727724[18] = -9.8100000000000005*cos(state[0])*cos(state[1]);
   out_8659941392114727724[19] = 9.8100000000000005*sin(state[0])*sin(state[1]);
   out_8659941392114727724[20] = 0;
   out_8659941392114727724[21] = state[8];
   out_8659941392114727724[22] = 0;
   out_8659941392114727724[23] = -state[6];
   out_8659941392114727724[24] = -state[5];
   out_8659941392114727724[25] = 0;
   out_8659941392114727724[26] = state[3];
   out_8659941392114727724[27] = 0;
   out_8659941392114727724[28] = 0;
   out_8659941392114727724[29] = 0;
   out_8659941392114727724[30] = 0;
   out_8659941392114727724[31] = 1;
   out_8659941392114727724[32] = 0;
   out_8659941392114727724[33] = 0;
   out_8659941392114727724[34] = 1;
   out_8659941392114727724[35] = 0;
   out_8659941392114727724[36] = 9.8100000000000005*sin(state[0])*cos(state[1]);
   out_8659941392114727724[37] = 9.8100000000000005*sin(state[1])*cos(state[0]);
   out_8659941392114727724[38] = 0;
   out_8659941392114727724[39] = -state[7];
   out_8659941392114727724[40] = state[6];
   out_8659941392114727724[41] = 0;
   out_8659941392114727724[42] = state[4];
   out_8659941392114727724[43] = -state[3];
   out_8659941392114727724[44] = 0;
   out_8659941392114727724[45] = 0;
   out_8659941392114727724[46] = 0;
   out_8659941392114727724[47] = 0;
   out_8659941392114727724[48] = 0;
   out_8659941392114727724[49] = 0;
   out_8659941392114727724[50] = 1;
   out_8659941392114727724[51] = 0;
   out_8659941392114727724[52] = 0;
   out_8659941392114727724[53] = 1;
}
void h_13(double *state, double *unused, double *out_3800811769775255925) {
   out_3800811769775255925[0] = state[3];
   out_3800811769775255925[1] = state[4];
   out_3800811769775255925[2] = state[5];
}
void H_13(double *state, double *unused, double *out_8086131599605158234) {
   out_8086131599605158234[0] = 0;
   out_8086131599605158234[1] = 0;
   out_8086131599605158234[2] = 0;
   out_8086131599605158234[3] = 1;
   out_8086131599605158234[4] = 0;
   out_8086131599605158234[5] = 0;
   out_8086131599605158234[6] = 0;
   out_8086131599605158234[7] = 0;
   out_8086131599605158234[8] = 0;
   out_8086131599605158234[9] = 0;
   out_8086131599605158234[10] = 0;
   out_8086131599605158234[11] = 0;
   out_8086131599605158234[12] = 0;
   out_8086131599605158234[13] = 0;
   out_8086131599605158234[14] = 0;
   out_8086131599605158234[15] = 0;
   out_8086131599605158234[16] = 0;
   out_8086131599605158234[17] = 0;
   out_8086131599605158234[18] = 0;
   out_8086131599605158234[19] = 0;
   out_8086131599605158234[20] = 0;
   out_8086131599605158234[21] = 0;
   out_8086131599605158234[22] = 1;
   out_8086131599605158234[23] = 0;
   out_8086131599605158234[24] = 0;
   out_8086131599605158234[25] = 0;
   out_8086131599605158234[26] = 0;
   out_8086131599605158234[27] = 0;
   out_8086131599605158234[28] = 0;
   out_8086131599605158234[29] = 0;
   out_8086131599605158234[30] = 0;
   out_8086131599605158234[31] = 0;
   out_8086131599605158234[32] = 0;
   out_8086131599605158234[33] = 0;
   out_8086131599605158234[34] = 0;
   out_8086131599605158234[35] = 0;
   out_8086131599605158234[36] = 0;
   out_8086131599605158234[37] = 0;
   out_8086131599605158234[38] = 0;
   out_8086131599605158234[39] = 0;
   out_8086131599605158234[40] = 0;
   out_8086131599605158234[41] = 1;
   out_8086131599605158234[42] = 0;
   out_8086131599605158234[43] = 0;
   out_8086131599605158234[44] = 0;
   out_8086131599605158234[45] = 0;
   out_8086131599605158234[46] = 0;
   out_8086131599605158234[47] = 0;
   out_8086131599605158234[48] = 0;
   out_8086131599605158234[49] = 0;
   out_8086131599605158234[50] = 0;
   out_8086131599605158234[51] = 0;
   out_8086131599605158234[52] = 0;
   out_8086131599605158234[53] = 0;
}
void h_14(double *state, double *unused, double *out_4008947375398857851) {
   out_4008947375398857851[0] = state[6];
   out_4008947375398857851[1] = state[7];
   out_4008947375398857851[2] = state[8];
}
void H_14(double *state, double *unused, double *out_7335164568598006506) {
   out_7335164568598006506[0] = 0;
   out_7335164568598006506[1] = 0;
   out_7335164568598006506[2] = 0;
   out_7335164568598006506[3] = 0;
   out_7335164568598006506[4] = 0;
   out_7335164568598006506[5] = 0;
   out_7335164568598006506[6] = 1;
   out_7335164568598006506[7] = 0;
   out_7335164568598006506[8] = 0;
   out_7335164568598006506[9] = 0;
   out_7335164568598006506[10] = 0;
   out_7335164568598006506[11] = 0;
   out_7335164568598006506[12] = 0;
   out_7335164568598006506[13] = 0;
   out_7335164568598006506[14] = 0;
   out_7335164568598006506[15] = 0;
   out_7335164568598006506[16] = 0;
   out_7335164568598006506[17] = 0;
   out_7335164568598006506[18] = 0;
   out_7335164568598006506[19] = 0;
   out_7335164568598006506[20] = 0;
   out_7335164568598006506[21] = 0;
   out_7335164568598006506[22] = 0;
   out_7335164568598006506[23] = 0;
   out_7335164568598006506[24] = 0;
   out_7335164568598006506[25] = 1;
   out_7335164568598006506[26] = 0;
   out_7335164568598006506[27] = 0;
   out_7335164568598006506[28] = 0;
   out_7335164568598006506[29] = 0;
   out_7335164568598006506[30] = 0;
   out_7335164568598006506[31] = 0;
   out_7335164568598006506[32] = 0;
   out_7335164568598006506[33] = 0;
   out_7335164568598006506[34] = 0;
   out_7335164568598006506[35] = 0;
   out_7335164568598006506[36] = 0;
   out_7335164568598006506[37] = 0;
   out_7335164568598006506[38] = 0;
   out_7335164568598006506[39] = 0;
   out_7335164568598006506[40] = 0;
   out_7335164568598006506[41] = 0;
   out_7335164568598006506[42] = 0;
   out_7335164568598006506[43] = 0;
   out_7335164568598006506[44] = 1;
   out_7335164568598006506[45] = 0;
   out_7335164568598006506[46] = 0;
   out_7335164568598006506[47] = 0;
   out_7335164568598006506[48] = 0;
   out_7335164568598006506[49] = 0;
   out_7335164568598006506[50] = 0;
   out_7335164568598006506[51] = 0;
   out_7335164568598006506[52] = 0;
   out_7335164568598006506[53] = 0;
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
void pose_err_fun(double *nom_x, double *delta_x, double *out_8706376808260214389) {
  err_fun(nom_x, delta_x, out_8706376808260214389);
}
void pose_inv_err_fun(double *nom_x, double *true_x, double *out_1316013831039188305) {
  inv_err_fun(nom_x, true_x, out_1316013831039188305);
}
void pose_H_mod_fun(double *state, double *out_1995820263732979846) {
  H_mod_fun(state, out_1995820263732979846);
}
void pose_f_fun(double *state, double dt, double *out_1989172059616365876) {
  f_fun(state,  dt, out_1989172059616365876);
}
void pose_F_fun(double *state, double dt, double *out_1876162241026325508) {
  F_fun(state,  dt, out_1876162241026325508);
}
void pose_h_4(double *state, double *unused, double *out_8913681603248625200) {
  h_4(state, unused, out_8913681603248625200);
}
void pose_H_4(double *state, double *unused, double *out_7148338648772060581) {
  H_4(state, unused, out_7148338648772060581);
}
void pose_h_10(double *state, double *unused, double *out_5957325102648707682) {
  h_10(state, unused, out_5957325102648707682);
}
void pose_H_10(double *state, double *unused, double *out_8659941392114727724) {
  H_10(state, unused, out_8659941392114727724);
}
void pose_h_13(double *state, double *unused, double *out_3800811769775255925) {
  h_13(state, unused, out_3800811769775255925);
}
void pose_H_13(double *state, double *unused, double *out_8086131599605158234) {
  H_13(state, unused, out_8086131599605158234);
}
void pose_h_14(double *state, double *unused, double *out_4008947375398857851) {
  h_14(state, unused, out_4008947375398857851);
}
void pose_H_14(double *state, double *unused, double *out_7335164568598006506) {
  H_14(state, unused, out_7335164568598006506);
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
