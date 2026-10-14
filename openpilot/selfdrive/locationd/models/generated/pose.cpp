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
void err_fun(double *nom_x, double *delta_x, double *out_8587424029422482613) {
   out_8587424029422482613[0] = delta_x[0] + nom_x[0];
   out_8587424029422482613[1] = delta_x[1] + nom_x[1];
   out_8587424029422482613[2] = delta_x[2] + nom_x[2];
   out_8587424029422482613[3] = delta_x[3] + nom_x[3];
   out_8587424029422482613[4] = delta_x[4] + nom_x[4];
   out_8587424029422482613[5] = delta_x[5] + nom_x[5];
   out_8587424029422482613[6] = delta_x[6] + nom_x[6];
   out_8587424029422482613[7] = delta_x[7] + nom_x[7];
   out_8587424029422482613[8] = delta_x[8] + nom_x[8];
   out_8587424029422482613[9] = delta_x[9] + nom_x[9];
   out_8587424029422482613[10] = delta_x[10] + nom_x[10];
   out_8587424029422482613[11] = delta_x[11] + nom_x[11];
   out_8587424029422482613[12] = delta_x[12] + nom_x[12];
   out_8587424029422482613[13] = delta_x[13] + nom_x[13];
   out_8587424029422482613[14] = delta_x[14] + nom_x[14];
   out_8587424029422482613[15] = delta_x[15] + nom_x[15];
   out_8587424029422482613[16] = delta_x[16] + nom_x[16];
   out_8587424029422482613[17] = delta_x[17] + nom_x[17];
}
void inv_err_fun(double *nom_x, double *true_x, double *out_8786163150320395038) {
   out_8786163150320395038[0] = -nom_x[0] + true_x[0];
   out_8786163150320395038[1] = -nom_x[1] + true_x[1];
   out_8786163150320395038[2] = -nom_x[2] + true_x[2];
   out_8786163150320395038[3] = -nom_x[3] + true_x[3];
   out_8786163150320395038[4] = -nom_x[4] + true_x[4];
   out_8786163150320395038[5] = -nom_x[5] + true_x[5];
   out_8786163150320395038[6] = -nom_x[6] + true_x[6];
   out_8786163150320395038[7] = -nom_x[7] + true_x[7];
   out_8786163150320395038[8] = -nom_x[8] + true_x[8];
   out_8786163150320395038[9] = -nom_x[9] + true_x[9];
   out_8786163150320395038[10] = -nom_x[10] + true_x[10];
   out_8786163150320395038[11] = -nom_x[11] + true_x[11];
   out_8786163150320395038[12] = -nom_x[12] + true_x[12];
   out_8786163150320395038[13] = -nom_x[13] + true_x[13];
   out_8786163150320395038[14] = -nom_x[14] + true_x[14];
   out_8786163150320395038[15] = -nom_x[15] + true_x[15];
   out_8786163150320395038[16] = -nom_x[16] + true_x[16];
   out_8786163150320395038[17] = -nom_x[17] + true_x[17];
}
void H_mod_fun(double *state, double *out_2404492370394702667) {
   out_2404492370394702667[0] = 1.0;
   out_2404492370394702667[1] = 0.0;
   out_2404492370394702667[2] = 0.0;
   out_2404492370394702667[3] = 0.0;
   out_2404492370394702667[4] = 0.0;
   out_2404492370394702667[5] = 0.0;
   out_2404492370394702667[6] = 0.0;
   out_2404492370394702667[7] = 0.0;
   out_2404492370394702667[8] = 0.0;
   out_2404492370394702667[9] = 0.0;
   out_2404492370394702667[10] = 0.0;
   out_2404492370394702667[11] = 0.0;
   out_2404492370394702667[12] = 0.0;
   out_2404492370394702667[13] = 0.0;
   out_2404492370394702667[14] = 0.0;
   out_2404492370394702667[15] = 0.0;
   out_2404492370394702667[16] = 0.0;
   out_2404492370394702667[17] = 0.0;
   out_2404492370394702667[18] = 0.0;
   out_2404492370394702667[19] = 1.0;
   out_2404492370394702667[20] = 0.0;
   out_2404492370394702667[21] = 0.0;
   out_2404492370394702667[22] = 0.0;
   out_2404492370394702667[23] = 0.0;
   out_2404492370394702667[24] = 0.0;
   out_2404492370394702667[25] = 0.0;
   out_2404492370394702667[26] = 0.0;
   out_2404492370394702667[27] = 0.0;
   out_2404492370394702667[28] = 0.0;
   out_2404492370394702667[29] = 0.0;
   out_2404492370394702667[30] = 0.0;
   out_2404492370394702667[31] = 0.0;
   out_2404492370394702667[32] = 0.0;
   out_2404492370394702667[33] = 0.0;
   out_2404492370394702667[34] = 0.0;
   out_2404492370394702667[35] = 0.0;
   out_2404492370394702667[36] = 0.0;
   out_2404492370394702667[37] = 0.0;
   out_2404492370394702667[38] = 1.0;
   out_2404492370394702667[39] = 0.0;
   out_2404492370394702667[40] = 0.0;
   out_2404492370394702667[41] = 0.0;
   out_2404492370394702667[42] = 0.0;
   out_2404492370394702667[43] = 0.0;
   out_2404492370394702667[44] = 0.0;
   out_2404492370394702667[45] = 0.0;
   out_2404492370394702667[46] = 0.0;
   out_2404492370394702667[47] = 0.0;
   out_2404492370394702667[48] = 0.0;
   out_2404492370394702667[49] = 0.0;
   out_2404492370394702667[50] = 0.0;
   out_2404492370394702667[51] = 0.0;
   out_2404492370394702667[52] = 0.0;
   out_2404492370394702667[53] = 0.0;
   out_2404492370394702667[54] = 0.0;
   out_2404492370394702667[55] = 0.0;
   out_2404492370394702667[56] = 0.0;
   out_2404492370394702667[57] = 1.0;
   out_2404492370394702667[58] = 0.0;
   out_2404492370394702667[59] = 0.0;
   out_2404492370394702667[60] = 0.0;
   out_2404492370394702667[61] = 0.0;
   out_2404492370394702667[62] = 0.0;
   out_2404492370394702667[63] = 0.0;
   out_2404492370394702667[64] = 0.0;
   out_2404492370394702667[65] = 0.0;
   out_2404492370394702667[66] = 0.0;
   out_2404492370394702667[67] = 0.0;
   out_2404492370394702667[68] = 0.0;
   out_2404492370394702667[69] = 0.0;
   out_2404492370394702667[70] = 0.0;
   out_2404492370394702667[71] = 0.0;
   out_2404492370394702667[72] = 0.0;
   out_2404492370394702667[73] = 0.0;
   out_2404492370394702667[74] = 0.0;
   out_2404492370394702667[75] = 0.0;
   out_2404492370394702667[76] = 1.0;
   out_2404492370394702667[77] = 0.0;
   out_2404492370394702667[78] = 0.0;
   out_2404492370394702667[79] = 0.0;
   out_2404492370394702667[80] = 0.0;
   out_2404492370394702667[81] = 0.0;
   out_2404492370394702667[82] = 0.0;
   out_2404492370394702667[83] = 0.0;
   out_2404492370394702667[84] = 0.0;
   out_2404492370394702667[85] = 0.0;
   out_2404492370394702667[86] = 0.0;
   out_2404492370394702667[87] = 0.0;
   out_2404492370394702667[88] = 0.0;
   out_2404492370394702667[89] = 0.0;
   out_2404492370394702667[90] = 0.0;
   out_2404492370394702667[91] = 0.0;
   out_2404492370394702667[92] = 0.0;
   out_2404492370394702667[93] = 0.0;
   out_2404492370394702667[94] = 0.0;
   out_2404492370394702667[95] = 1.0;
   out_2404492370394702667[96] = 0.0;
   out_2404492370394702667[97] = 0.0;
   out_2404492370394702667[98] = 0.0;
   out_2404492370394702667[99] = 0.0;
   out_2404492370394702667[100] = 0.0;
   out_2404492370394702667[101] = 0.0;
   out_2404492370394702667[102] = 0.0;
   out_2404492370394702667[103] = 0.0;
   out_2404492370394702667[104] = 0.0;
   out_2404492370394702667[105] = 0.0;
   out_2404492370394702667[106] = 0.0;
   out_2404492370394702667[107] = 0.0;
   out_2404492370394702667[108] = 0.0;
   out_2404492370394702667[109] = 0.0;
   out_2404492370394702667[110] = 0.0;
   out_2404492370394702667[111] = 0.0;
   out_2404492370394702667[112] = 0.0;
   out_2404492370394702667[113] = 0.0;
   out_2404492370394702667[114] = 1.0;
   out_2404492370394702667[115] = 0.0;
   out_2404492370394702667[116] = 0.0;
   out_2404492370394702667[117] = 0.0;
   out_2404492370394702667[118] = 0.0;
   out_2404492370394702667[119] = 0.0;
   out_2404492370394702667[120] = 0.0;
   out_2404492370394702667[121] = 0.0;
   out_2404492370394702667[122] = 0.0;
   out_2404492370394702667[123] = 0.0;
   out_2404492370394702667[124] = 0.0;
   out_2404492370394702667[125] = 0.0;
   out_2404492370394702667[126] = 0.0;
   out_2404492370394702667[127] = 0.0;
   out_2404492370394702667[128] = 0.0;
   out_2404492370394702667[129] = 0.0;
   out_2404492370394702667[130] = 0.0;
   out_2404492370394702667[131] = 0.0;
   out_2404492370394702667[132] = 0.0;
   out_2404492370394702667[133] = 1.0;
   out_2404492370394702667[134] = 0.0;
   out_2404492370394702667[135] = 0.0;
   out_2404492370394702667[136] = 0.0;
   out_2404492370394702667[137] = 0.0;
   out_2404492370394702667[138] = 0.0;
   out_2404492370394702667[139] = 0.0;
   out_2404492370394702667[140] = 0.0;
   out_2404492370394702667[141] = 0.0;
   out_2404492370394702667[142] = 0.0;
   out_2404492370394702667[143] = 0.0;
   out_2404492370394702667[144] = 0.0;
   out_2404492370394702667[145] = 0.0;
   out_2404492370394702667[146] = 0.0;
   out_2404492370394702667[147] = 0.0;
   out_2404492370394702667[148] = 0.0;
   out_2404492370394702667[149] = 0.0;
   out_2404492370394702667[150] = 0.0;
   out_2404492370394702667[151] = 0.0;
   out_2404492370394702667[152] = 1.0;
   out_2404492370394702667[153] = 0.0;
   out_2404492370394702667[154] = 0.0;
   out_2404492370394702667[155] = 0.0;
   out_2404492370394702667[156] = 0.0;
   out_2404492370394702667[157] = 0.0;
   out_2404492370394702667[158] = 0.0;
   out_2404492370394702667[159] = 0.0;
   out_2404492370394702667[160] = 0.0;
   out_2404492370394702667[161] = 0.0;
   out_2404492370394702667[162] = 0.0;
   out_2404492370394702667[163] = 0.0;
   out_2404492370394702667[164] = 0.0;
   out_2404492370394702667[165] = 0.0;
   out_2404492370394702667[166] = 0.0;
   out_2404492370394702667[167] = 0.0;
   out_2404492370394702667[168] = 0.0;
   out_2404492370394702667[169] = 0.0;
   out_2404492370394702667[170] = 0.0;
   out_2404492370394702667[171] = 1.0;
   out_2404492370394702667[172] = 0.0;
   out_2404492370394702667[173] = 0.0;
   out_2404492370394702667[174] = 0.0;
   out_2404492370394702667[175] = 0.0;
   out_2404492370394702667[176] = 0.0;
   out_2404492370394702667[177] = 0.0;
   out_2404492370394702667[178] = 0.0;
   out_2404492370394702667[179] = 0.0;
   out_2404492370394702667[180] = 0.0;
   out_2404492370394702667[181] = 0.0;
   out_2404492370394702667[182] = 0.0;
   out_2404492370394702667[183] = 0.0;
   out_2404492370394702667[184] = 0.0;
   out_2404492370394702667[185] = 0.0;
   out_2404492370394702667[186] = 0.0;
   out_2404492370394702667[187] = 0.0;
   out_2404492370394702667[188] = 0.0;
   out_2404492370394702667[189] = 0.0;
   out_2404492370394702667[190] = 1.0;
   out_2404492370394702667[191] = 0.0;
   out_2404492370394702667[192] = 0.0;
   out_2404492370394702667[193] = 0.0;
   out_2404492370394702667[194] = 0.0;
   out_2404492370394702667[195] = 0.0;
   out_2404492370394702667[196] = 0.0;
   out_2404492370394702667[197] = 0.0;
   out_2404492370394702667[198] = 0.0;
   out_2404492370394702667[199] = 0.0;
   out_2404492370394702667[200] = 0.0;
   out_2404492370394702667[201] = 0.0;
   out_2404492370394702667[202] = 0.0;
   out_2404492370394702667[203] = 0.0;
   out_2404492370394702667[204] = 0.0;
   out_2404492370394702667[205] = 0.0;
   out_2404492370394702667[206] = 0.0;
   out_2404492370394702667[207] = 0.0;
   out_2404492370394702667[208] = 0.0;
   out_2404492370394702667[209] = 1.0;
   out_2404492370394702667[210] = 0.0;
   out_2404492370394702667[211] = 0.0;
   out_2404492370394702667[212] = 0.0;
   out_2404492370394702667[213] = 0.0;
   out_2404492370394702667[214] = 0.0;
   out_2404492370394702667[215] = 0.0;
   out_2404492370394702667[216] = 0.0;
   out_2404492370394702667[217] = 0.0;
   out_2404492370394702667[218] = 0.0;
   out_2404492370394702667[219] = 0.0;
   out_2404492370394702667[220] = 0.0;
   out_2404492370394702667[221] = 0.0;
   out_2404492370394702667[222] = 0.0;
   out_2404492370394702667[223] = 0.0;
   out_2404492370394702667[224] = 0.0;
   out_2404492370394702667[225] = 0.0;
   out_2404492370394702667[226] = 0.0;
   out_2404492370394702667[227] = 0.0;
   out_2404492370394702667[228] = 1.0;
   out_2404492370394702667[229] = 0.0;
   out_2404492370394702667[230] = 0.0;
   out_2404492370394702667[231] = 0.0;
   out_2404492370394702667[232] = 0.0;
   out_2404492370394702667[233] = 0.0;
   out_2404492370394702667[234] = 0.0;
   out_2404492370394702667[235] = 0.0;
   out_2404492370394702667[236] = 0.0;
   out_2404492370394702667[237] = 0.0;
   out_2404492370394702667[238] = 0.0;
   out_2404492370394702667[239] = 0.0;
   out_2404492370394702667[240] = 0.0;
   out_2404492370394702667[241] = 0.0;
   out_2404492370394702667[242] = 0.0;
   out_2404492370394702667[243] = 0.0;
   out_2404492370394702667[244] = 0.0;
   out_2404492370394702667[245] = 0.0;
   out_2404492370394702667[246] = 0.0;
   out_2404492370394702667[247] = 1.0;
   out_2404492370394702667[248] = 0.0;
   out_2404492370394702667[249] = 0.0;
   out_2404492370394702667[250] = 0.0;
   out_2404492370394702667[251] = 0.0;
   out_2404492370394702667[252] = 0.0;
   out_2404492370394702667[253] = 0.0;
   out_2404492370394702667[254] = 0.0;
   out_2404492370394702667[255] = 0.0;
   out_2404492370394702667[256] = 0.0;
   out_2404492370394702667[257] = 0.0;
   out_2404492370394702667[258] = 0.0;
   out_2404492370394702667[259] = 0.0;
   out_2404492370394702667[260] = 0.0;
   out_2404492370394702667[261] = 0.0;
   out_2404492370394702667[262] = 0.0;
   out_2404492370394702667[263] = 0.0;
   out_2404492370394702667[264] = 0.0;
   out_2404492370394702667[265] = 0.0;
   out_2404492370394702667[266] = 1.0;
   out_2404492370394702667[267] = 0.0;
   out_2404492370394702667[268] = 0.0;
   out_2404492370394702667[269] = 0.0;
   out_2404492370394702667[270] = 0.0;
   out_2404492370394702667[271] = 0.0;
   out_2404492370394702667[272] = 0.0;
   out_2404492370394702667[273] = 0.0;
   out_2404492370394702667[274] = 0.0;
   out_2404492370394702667[275] = 0.0;
   out_2404492370394702667[276] = 0.0;
   out_2404492370394702667[277] = 0.0;
   out_2404492370394702667[278] = 0.0;
   out_2404492370394702667[279] = 0.0;
   out_2404492370394702667[280] = 0.0;
   out_2404492370394702667[281] = 0.0;
   out_2404492370394702667[282] = 0.0;
   out_2404492370394702667[283] = 0.0;
   out_2404492370394702667[284] = 0.0;
   out_2404492370394702667[285] = 1.0;
   out_2404492370394702667[286] = 0.0;
   out_2404492370394702667[287] = 0.0;
   out_2404492370394702667[288] = 0.0;
   out_2404492370394702667[289] = 0.0;
   out_2404492370394702667[290] = 0.0;
   out_2404492370394702667[291] = 0.0;
   out_2404492370394702667[292] = 0.0;
   out_2404492370394702667[293] = 0.0;
   out_2404492370394702667[294] = 0.0;
   out_2404492370394702667[295] = 0.0;
   out_2404492370394702667[296] = 0.0;
   out_2404492370394702667[297] = 0.0;
   out_2404492370394702667[298] = 0.0;
   out_2404492370394702667[299] = 0.0;
   out_2404492370394702667[300] = 0.0;
   out_2404492370394702667[301] = 0.0;
   out_2404492370394702667[302] = 0.0;
   out_2404492370394702667[303] = 0.0;
   out_2404492370394702667[304] = 1.0;
   out_2404492370394702667[305] = 0.0;
   out_2404492370394702667[306] = 0.0;
   out_2404492370394702667[307] = 0.0;
   out_2404492370394702667[308] = 0.0;
   out_2404492370394702667[309] = 0.0;
   out_2404492370394702667[310] = 0.0;
   out_2404492370394702667[311] = 0.0;
   out_2404492370394702667[312] = 0.0;
   out_2404492370394702667[313] = 0.0;
   out_2404492370394702667[314] = 0.0;
   out_2404492370394702667[315] = 0.0;
   out_2404492370394702667[316] = 0.0;
   out_2404492370394702667[317] = 0.0;
   out_2404492370394702667[318] = 0.0;
   out_2404492370394702667[319] = 0.0;
   out_2404492370394702667[320] = 0.0;
   out_2404492370394702667[321] = 0.0;
   out_2404492370394702667[322] = 0.0;
   out_2404492370394702667[323] = 1.0;
}
void f_fun(double *state, double dt, double *out_442464745730678105) {
   out_442464745730678105[0] = atan2((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), -(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]));
   out_442464745730678105[1] = asin(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]));
   out_442464745730678105[2] = atan2(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), -(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]));
   out_442464745730678105[3] = dt*state[12] + state[3];
   out_442464745730678105[4] = dt*state[13] + state[4];
   out_442464745730678105[5] = dt*state[14] + state[5];
   out_442464745730678105[6] = state[6];
   out_442464745730678105[7] = state[7];
   out_442464745730678105[8] = state[8];
   out_442464745730678105[9] = state[9];
   out_442464745730678105[10] = state[10];
   out_442464745730678105[11] = state[11];
   out_442464745730678105[12] = state[12];
   out_442464745730678105[13] = state[13];
   out_442464745730678105[14] = state[14];
   out_442464745730678105[15] = state[15];
   out_442464745730678105[16] = state[16];
   out_442464745730678105[17] = state[17];
}
void F_fun(double *state, double dt, double *out_68862599699564370) {
   out_68862599699564370[0] = ((-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*cos(state[0])*cos(state[1]) - sin(state[0])*cos(dt*state[6])*cos(dt*state[7])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + ((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*cos(state[0])*cos(state[1]) - sin(dt*state[6])*sin(state[0])*cos(dt*state[7])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_68862599699564370[1] = ((-sin(dt*state[6])*sin(dt*state[8]) - sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*cos(state[1]) - (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*sin(state[1]) - sin(state[1])*cos(dt*state[6])*cos(dt*state[7])*cos(state[0]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*sin(state[1]) + (-sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) + sin(dt*state[8])*cos(dt*state[6]))*cos(state[1]) - sin(dt*state[6])*sin(state[1])*cos(dt*state[7])*cos(state[0]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_68862599699564370[2] = 0;
   out_68862599699564370[3] = 0;
   out_68862599699564370[4] = 0;
   out_68862599699564370[5] = 0;
   out_68862599699564370[6] = (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(dt*cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*sin(dt*state[8]) - dt*sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-dt*sin(dt*state[6])*cos(dt*state[8]) + dt*sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) - dt*cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (dt*sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_68862599699564370[7] = (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[6])*sin(dt*state[7])*cos(state[0])*cos(state[1]) + dt*sin(dt*state[6])*sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) - dt*sin(dt*state[6])*sin(state[1])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[7])*cos(dt*state[6])*cos(state[0])*cos(state[1]) + dt*sin(dt*state[8])*sin(state[0])*cos(dt*state[6])*cos(dt*state[7])*cos(state[1]) - dt*sin(state[1])*cos(dt*state[6])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_68862599699564370[8] = ((dt*sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + dt*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (dt*sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + ((dt*sin(dt*state[6])*sin(dt*state[8]) + dt*sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*cos(dt*state[8]) + dt*sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_68862599699564370[9] = 0;
   out_68862599699564370[10] = 0;
   out_68862599699564370[11] = 0;
   out_68862599699564370[12] = 0;
   out_68862599699564370[13] = 0;
   out_68862599699564370[14] = 0;
   out_68862599699564370[15] = 0;
   out_68862599699564370[16] = 0;
   out_68862599699564370[17] = 0;
   out_68862599699564370[18] = (-sin(dt*state[7])*sin(state[0])*cos(state[1]) - sin(dt*state[8])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_68862599699564370[19] = (-sin(dt*state[7])*sin(state[1])*cos(state[0]) + sin(dt*state[8])*sin(state[0])*sin(state[1])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_68862599699564370[20] = 0;
   out_68862599699564370[21] = 0;
   out_68862599699564370[22] = 0;
   out_68862599699564370[23] = 0;
   out_68862599699564370[24] = 0;
   out_68862599699564370[25] = (dt*sin(dt*state[7])*sin(dt*state[8])*sin(state[0])*cos(state[1]) - dt*sin(dt*state[7])*sin(state[1])*cos(dt*state[8]) + dt*cos(dt*state[7])*cos(state[0])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_68862599699564370[26] = (-dt*sin(dt*state[8])*sin(state[1])*cos(dt*state[7]) - dt*sin(state[0])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_68862599699564370[27] = 0;
   out_68862599699564370[28] = 0;
   out_68862599699564370[29] = 0;
   out_68862599699564370[30] = 0;
   out_68862599699564370[31] = 0;
   out_68862599699564370[32] = 0;
   out_68862599699564370[33] = 0;
   out_68862599699564370[34] = 0;
   out_68862599699564370[35] = 0;
   out_68862599699564370[36] = ((sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[7]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[7]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_68862599699564370[37] = (-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(-sin(dt*state[7])*sin(state[2])*cos(state[0])*cos(state[1]) + sin(dt*state[8])*sin(state[0])*sin(state[2])*cos(dt*state[7])*cos(state[1]) - sin(state[1])*sin(state[2])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*(-sin(dt*state[7])*cos(state[0])*cos(state[1])*cos(state[2]) + sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1])*cos(state[2]) - sin(state[1])*cos(dt*state[7])*cos(dt*state[8])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_68862599699564370[38] = ((-sin(state[0])*sin(state[2]) - sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (-sin(state[0])*sin(state[1])*sin(state[2]) - cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_68862599699564370[39] = 0;
   out_68862599699564370[40] = 0;
   out_68862599699564370[41] = 0;
   out_68862599699564370[42] = 0;
   out_68862599699564370[43] = (-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(dt*(sin(state[0])*cos(state[2]) - sin(state[1])*sin(state[2])*cos(state[0]))*cos(dt*state[7]) - dt*(sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[7])*sin(dt*state[8]) - dt*sin(dt*state[7])*sin(state[2])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*(dt*(-sin(state[0])*sin(state[2]) - sin(state[1])*cos(state[0])*cos(state[2]))*cos(dt*state[7]) - dt*(sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[7])*sin(dt*state[8]) - dt*sin(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_68862599699564370[44] = (dt*(sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*cos(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*sin(state[2])*cos(dt*state[7])*cos(state[1]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + (dt*(sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*cos(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[7])*cos(state[1])*cos(state[2]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_68862599699564370[45] = 0;
   out_68862599699564370[46] = 0;
   out_68862599699564370[47] = 0;
   out_68862599699564370[48] = 0;
   out_68862599699564370[49] = 0;
   out_68862599699564370[50] = 0;
   out_68862599699564370[51] = 0;
   out_68862599699564370[52] = 0;
   out_68862599699564370[53] = 0;
   out_68862599699564370[54] = 0;
   out_68862599699564370[55] = 0;
   out_68862599699564370[56] = 0;
   out_68862599699564370[57] = 1;
   out_68862599699564370[58] = 0;
   out_68862599699564370[59] = 0;
   out_68862599699564370[60] = 0;
   out_68862599699564370[61] = 0;
   out_68862599699564370[62] = 0;
   out_68862599699564370[63] = 0;
   out_68862599699564370[64] = 0;
   out_68862599699564370[65] = 0;
   out_68862599699564370[66] = dt;
   out_68862599699564370[67] = 0;
   out_68862599699564370[68] = 0;
   out_68862599699564370[69] = 0;
   out_68862599699564370[70] = 0;
   out_68862599699564370[71] = 0;
   out_68862599699564370[72] = 0;
   out_68862599699564370[73] = 0;
   out_68862599699564370[74] = 0;
   out_68862599699564370[75] = 0;
   out_68862599699564370[76] = 1;
   out_68862599699564370[77] = 0;
   out_68862599699564370[78] = 0;
   out_68862599699564370[79] = 0;
   out_68862599699564370[80] = 0;
   out_68862599699564370[81] = 0;
   out_68862599699564370[82] = 0;
   out_68862599699564370[83] = 0;
   out_68862599699564370[84] = 0;
   out_68862599699564370[85] = dt;
   out_68862599699564370[86] = 0;
   out_68862599699564370[87] = 0;
   out_68862599699564370[88] = 0;
   out_68862599699564370[89] = 0;
   out_68862599699564370[90] = 0;
   out_68862599699564370[91] = 0;
   out_68862599699564370[92] = 0;
   out_68862599699564370[93] = 0;
   out_68862599699564370[94] = 0;
   out_68862599699564370[95] = 1;
   out_68862599699564370[96] = 0;
   out_68862599699564370[97] = 0;
   out_68862599699564370[98] = 0;
   out_68862599699564370[99] = 0;
   out_68862599699564370[100] = 0;
   out_68862599699564370[101] = 0;
   out_68862599699564370[102] = 0;
   out_68862599699564370[103] = 0;
   out_68862599699564370[104] = dt;
   out_68862599699564370[105] = 0;
   out_68862599699564370[106] = 0;
   out_68862599699564370[107] = 0;
   out_68862599699564370[108] = 0;
   out_68862599699564370[109] = 0;
   out_68862599699564370[110] = 0;
   out_68862599699564370[111] = 0;
   out_68862599699564370[112] = 0;
   out_68862599699564370[113] = 0;
   out_68862599699564370[114] = 1;
   out_68862599699564370[115] = 0;
   out_68862599699564370[116] = 0;
   out_68862599699564370[117] = 0;
   out_68862599699564370[118] = 0;
   out_68862599699564370[119] = 0;
   out_68862599699564370[120] = 0;
   out_68862599699564370[121] = 0;
   out_68862599699564370[122] = 0;
   out_68862599699564370[123] = 0;
   out_68862599699564370[124] = 0;
   out_68862599699564370[125] = 0;
   out_68862599699564370[126] = 0;
   out_68862599699564370[127] = 0;
   out_68862599699564370[128] = 0;
   out_68862599699564370[129] = 0;
   out_68862599699564370[130] = 0;
   out_68862599699564370[131] = 0;
   out_68862599699564370[132] = 0;
   out_68862599699564370[133] = 1;
   out_68862599699564370[134] = 0;
   out_68862599699564370[135] = 0;
   out_68862599699564370[136] = 0;
   out_68862599699564370[137] = 0;
   out_68862599699564370[138] = 0;
   out_68862599699564370[139] = 0;
   out_68862599699564370[140] = 0;
   out_68862599699564370[141] = 0;
   out_68862599699564370[142] = 0;
   out_68862599699564370[143] = 0;
   out_68862599699564370[144] = 0;
   out_68862599699564370[145] = 0;
   out_68862599699564370[146] = 0;
   out_68862599699564370[147] = 0;
   out_68862599699564370[148] = 0;
   out_68862599699564370[149] = 0;
   out_68862599699564370[150] = 0;
   out_68862599699564370[151] = 0;
   out_68862599699564370[152] = 1;
   out_68862599699564370[153] = 0;
   out_68862599699564370[154] = 0;
   out_68862599699564370[155] = 0;
   out_68862599699564370[156] = 0;
   out_68862599699564370[157] = 0;
   out_68862599699564370[158] = 0;
   out_68862599699564370[159] = 0;
   out_68862599699564370[160] = 0;
   out_68862599699564370[161] = 0;
   out_68862599699564370[162] = 0;
   out_68862599699564370[163] = 0;
   out_68862599699564370[164] = 0;
   out_68862599699564370[165] = 0;
   out_68862599699564370[166] = 0;
   out_68862599699564370[167] = 0;
   out_68862599699564370[168] = 0;
   out_68862599699564370[169] = 0;
   out_68862599699564370[170] = 0;
   out_68862599699564370[171] = 1;
   out_68862599699564370[172] = 0;
   out_68862599699564370[173] = 0;
   out_68862599699564370[174] = 0;
   out_68862599699564370[175] = 0;
   out_68862599699564370[176] = 0;
   out_68862599699564370[177] = 0;
   out_68862599699564370[178] = 0;
   out_68862599699564370[179] = 0;
   out_68862599699564370[180] = 0;
   out_68862599699564370[181] = 0;
   out_68862599699564370[182] = 0;
   out_68862599699564370[183] = 0;
   out_68862599699564370[184] = 0;
   out_68862599699564370[185] = 0;
   out_68862599699564370[186] = 0;
   out_68862599699564370[187] = 0;
   out_68862599699564370[188] = 0;
   out_68862599699564370[189] = 0;
   out_68862599699564370[190] = 1;
   out_68862599699564370[191] = 0;
   out_68862599699564370[192] = 0;
   out_68862599699564370[193] = 0;
   out_68862599699564370[194] = 0;
   out_68862599699564370[195] = 0;
   out_68862599699564370[196] = 0;
   out_68862599699564370[197] = 0;
   out_68862599699564370[198] = 0;
   out_68862599699564370[199] = 0;
   out_68862599699564370[200] = 0;
   out_68862599699564370[201] = 0;
   out_68862599699564370[202] = 0;
   out_68862599699564370[203] = 0;
   out_68862599699564370[204] = 0;
   out_68862599699564370[205] = 0;
   out_68862599699564370[206] = 0;
   out_68862599699564370[207] = 0;
   out_68862599699564370[208] = 0;
   out_68862599699564370[209] = 1;
   out_68862599699564370[210] = 0;
   out_68862599699564370[211] = 0;
   out_68862599699564370[212] = 0;
   out_68862599699564370[213] = 0;
   out_68862599699564370[214] = 0;
   out_68862599699564370[215] = 0;
   out_68862599699564370[216] = 0;
   out_68862599699564370[217] = 0;
   out_68862599699564370[218] = 0;
   out_68862599699564370[219] = 0;
   out_68862599699564370[220] = 0;
   out_68862599699564370[221] = 0;
   out_68862599699564370[222] = 0;
   out_68862599699564370[223] = 0;
   out_68862599699564370[224] = 0;
   out_68862599699564370[225] = 0;
   out_68862599699564370[226] = 0;
   out_68862599699564370[227] = 0;
   out_68862599699564370[228] = 1;
   out_68862599699564370[229] = 0;
   out_68862599699564370[230] = 0;
   out_68862599699564370[231] = 0;
   out_68862599699564370[232] = 0;
   out_68862599699564370[233] = 0;
   out_68862599699564370[234] = 0;
   out_68862599699564370[235] = 0;
   out_68862599699564370[236] = 0;
   out_68862599699564370[237] = 0;
   out_68862599699564370[238] = 0;
   out_68862599699564370[239] = 0;
   out_68862599699564370[240] = 0;
   out_68862599699564370[241] = 0;
   out_68862599699564370[242] = 0;
   out_68862599699564370[243] = 0;
   out_68862599699564370[244] = 0;
   out_68862599699564370[245] = 0;
   out_68862599699564370[246] = 0;
   out_68862599699564370[247] = 1;
   out_68862599699564370[248] = 0;
   out_68862599699564370[249] = 0;
   out_68862599699564370[250] = 0;
   out_68862599699564370[251] = 0;
   out_68862599699564370[252] = 0;
   out_68862599699564370[253] = 0;
   out_68862599699564370[254] = 0;
   out_68862599699564370[255] = 0;
   out_68862599699564370[256] = 0;
   out_68862599699564370[257] = 0;
   out_68862599699564370[258] = 0;
   out_68862599699564370[259] = 0;
   out_68862599699564370[260] = 0;
   out_68862599699564370[261] = 0;
   out_68862599699564370[262] = 0;
   out_68862599699564370[263] = 0;
   out_68862599699564370[264] = 0;
   out_68862599699564370[265] = 0;
   out_68862599699564370[266] = 1;
   out_68862599699564370[267] = 0;
   out_68862599699564370[268] = 0;
   out_68862599699564370[269] = 0;
   out_68862599699564370[270] = 0;
   out_68862599699564370[271] = 0;
   out_68862599699564370[272] = 0;
   out_68862599699564370[273] = 0;
   out_68862599699564370[274] = 0;
   out_68862599699564370[275] = 0;
   out_68862599699564370[276] = 0;
   out_68862599699564370[277] = 0;
   out_68862599699564370[278] = 0;
   out_68862599699564370[279] = 0;
   out_68862599699564370[280] = 0;
   out_68862599699564370[281] = 0;
   out_68862599699564370[282] = 0;
   out_68862599699564370[283] = 0;
   out_68862599699564370[284] = 0;
   out_68862599699564370[285] = 1;
   out_68862599699564370[286] = 0;
   out_68862599699564370[287] = 0;
   out_68862599699564370[288] = 0;
   out_68862599699564370[289] = 0;
   out_68862599699564370[290] = 0;
   out_68862599699564370[291] = 0;
   out_68862599699564370[292] = 0;
   out_68862599699564370[293] = 0;
   out_68862599699564370[294] = 0;
   out_68862599699564370[295] = 0;
   out_68862599699564370[296] = 0;
   out_68862599699564370[297] = 0;
   out_68862599699564370[298] = 0;
   out_68862599699564370[299] = 0;
   out_68862599699564370[300] = 0;
   out_68862599699564370[301] = 0;
   out_68862599699564370[302] = 0;
   out_68862599699564370[303] = 0;
   out_68862599699564370[304] = 1;
   out_68862599699564370[305] = 0;
   out_68862599699564370[306] = 0;
   out_68862599699564370[307] = 0;
   out_68862599699564370[308] = 0;
   out_68862599699564370[309] = 0;
   out_68862599699564370[310] = 0;
   out_68862599699564370[311] = 0;
   out_68862599699564370[312] = 0;
   out_68862599699564370[313] = 0;
   out_68862599699564370[314] = 0;
   out_68862599699564370[315] = 0;
   out_68862599699564370[316] = 0;
   out_68862599699564370[317] = 0;
   out_68862599699564370[318] = 0;
   out_68862599699564370[319] = 0;
   out_68862599699564370[320] = 0;
   out_68862599699564370[321] = 0;
   out_68862599699564370[322] = 0;
   out_68862599699564370[323] = 1;
}
void h_4(double *state, double *unused, double *out_6968799398651119641) {
   out_6968799398651119641[0] = state[6] + state[9];
   out_6968799398651119641[1] = state[7] + state[10];
   out_6968799398651119641[2] = state[8] + state[11];
}
void H_4(double *state, double *unused, double *out_6333703861688286471) {
   out_6333703861688286471[0] = 0;
   out_6333703861688286471[1] = 0;
   out_6333703861688286471[2] = 0;
   out_6333703861688286471[3] = 0;
   out_6333703861688286471[4] = 0;
   out_6333703861688286471[5] = 0;
   out_6333703861688286471[6] = 1;
   out_6333703861688286471[7] = 0;
   out_6333703861688286471[8] = 0;
   out_6333703861688286471[9] = 1;
   out_6333703861688286471[10] = 0;
   out_6333703861688286471[11] = 0;
   out_6333703861688286471[12] = 0;
   out_6333703861688286471[13] = 0;
   out_6333703861688286471[14] = 0;
   out_6333703861688286471[15] = 0;
   out_6333703861688286471[16] = 0;
   out_6333703861688286471[17] = 0;
   out_6333703861688286471[18] = 0;
   out_6333703861688286471[19] = 0;
   out_6333703861688286471[20] = 0;
   out_6333703861688286471[21] = 0;
   out_6333703861688286471[22] = 0;
   out_6333703861688286471[23] = 0;
   out_6333703861688286471[24] = 0;
   out_6333703861688286471[25] = 1;
   out_6333703861688286471[26] = 0;
   out_6333703861688286471[27] = 0;
   out_6333703861688286471[28] = 1;
   out_6333703861688286471[29] = 0;
   out_6333703861688286471[30] = 0;
   out_6333703861688286471[31] = 0;
   out_6333703861688286471[32] = 0;
   out_6333703861688286471[33] = 0;
   out_6333703861688286471[34] = 0;
   out_6333703861688286471[35] = 0;
   out_6333703861688286471[36] = 0;
   out_6333703861688286471[37] = 0;
   out_6333703861688286471[38] = 0;
   out_6333703861688286471[39] = 0;
   out_6333703861688286471[40] = 0;
   out_6333703861688286471[41] = 0;
   out_6333703861688286471[42] = 0;
   out_6333703861688286471[43] = 0;
   out_6333703861688286471[44] = 1;
   out_6333703861688286471[45] = 0;
   out_6333703861688286471[46] = 0;
   out_6333703861688286471[47] = 1;
   out_6333703861688286471[48] = 0;
   out_6333703861688286471[49] = 0;
   out_6333703861688286471[50] = 0;
   out_6333703861688286471[51] = 0;
   out_6333703861688286471[52] = 0;
   out_6333703861688286471[53] = 0;
}
void h_10(double *state, double *unused, double *out_5068008641526453532) {
   out_5068008641526453532[0] = 9.8100000000000005*sin(state[1]) - state[4]*state[8] + state[5]*state[7] + state[12] + state[15];
   out_5068008641526453532[1] = -9.8100000000000005*sin(state[0])*cos(state[1]) + state[3]*state[8] - state[5]*state[6] + state[13] + state[16];
   out_5068008641526453532[2] = -9.8100000000000005*cos(state[0])*cos(state[1]) - state[3]*state[7] + state[4]*state[6] + state[14] + state[17];
}
void H_10(double *state, double *unused, double *out_3796470789070264043) {
   out_3796470789070264043[0] = 0;
   out_3796470789070264043[1] = 9.8100000000000005*cos(state[1]);
   out_3796470789070264043[2] = 0;
   out_3796470789070264043[3] = 0;
   out_3796470789070264043[4] = -state[8];
   out_3796470789070264043[5] = state[7];
   out_3796470789070264043[6] = 0;
   out_3796470789070264043[7] = state[5];
   out_3796470789070264043[8] = -state[4];
   out_3796470789070264043[9] = 0;
   out_3796470789070264043[10] = 0;
   out_3796470789070264043[11] = 0;
   out_3796470789070264043[12] = 1;
   out_3796470789070264043[13] = 0;
   out_3796470789070264043[14] = 0;
   out_3796470789070264043[15] = 1;
   out_3796470789070264043[16] = 0;
   out_3796470789070264043[17] = 0;
   out_3796470789070264043[18] = -9.8100000000000005*cos(state[0])*cos(state[1]);
   out_3796470789070264043[19] = 9.8100000000000005*sin(state[0])*sin(state[1]);
   out_3796470789070264043[20] = 0;
   out_3796470789070264043[21] = state[8];
   out_3796470789070264043[22] = 0;
   out_3796470789070264043[23] = -state[6];
   out_3796470789070264043[24] = -state[5];
   out_3796470789070264043[25] = 0;
   out_3796470789070264043[26] = state[3];
   out_3796470789070264043[27] = 0;
   out_3796470789070264043[28] = 0;
   out_3796470789070264043[29] = 0;
   out_3796470789070264043[30] = 0;
   out_3796470789070264043[31] = 1;
   out_3796470789070264043[32] = 0;
   out_3796470789070264043[33] = 0;
   out_3796470789070264043[34] = 1;
   out_3796470789070264043[35] = 0;
   out_3796470789070264043[36] = 9.8100000000000005*sin(state[0])*cos(state[1]);
   out_3796470789070264043[37] = 9.8100000000000005*sin(state[1])*cos(state[0]);
   out_3796470789070264043[38] = 0;
   out_3796470789070264043[39] = -state[7];
   out_3796470789070264043[40] = state[6];
   out_3796470789070264043[41] = 0;
   out_3796470789070264043[42] = state[4];
   out_3796470789070264043[43] = -state[3];
   out_3796470789070264043[44] = 0;
   out_3796470789070264043[45] = 0;
   out_3796470789070264043[46] = 0;
   out_3796470789070264043[47] = 0;
   out_3796470789070264043[48] = 0;
   out_3796470789070264043[49] = 0;
   out_3796470789070264043[50] = 1;
   out_3796470789070264043[51] = 0;
   out_3796470789070264043[52] = 0;
   out_3796470789070264043[53] = 1;
}
void h_13(double *state, double *unused, double *out_1215417763549020361) {
   out_1215417763549020361[0] = state[3];
   out_1215417763549020361[1] = state[4];
   out_1215417763549020361[2] = state[5];
}
void H_13(double *state, double *unused, double *out_8900766386688932344) {
   out_8900766386688932344[0] = 0;
   out_8900766386688932344[1] = 0;
   out_8900766386688932344[2] = 0;
   out_8900766386688932344[3] = 1;
   out_8900766386688932344[4] = 0;
   out_8900766386688932344[5] = 0;
   out_8900766386688932344[6] = 0;
   out_8900766386688932344[7] = 0;
   out_8900766386688932344[8] = 0;
   out_8900766386688932344[9] = 0;
   out_8900766386688932344[10] = 0;
   out_8900766386688932344[11] = 0;
   out_8900766386688932344[12] = 0;
   out_8900766386688932344[13] = 0;
   out_8900766386688932344[14] = 0;
   out_8900766386688932344[15] = 0;
   out_8900766386688932344[16] = 0;
   out_8900766386688932344[17] = 0;
   out_8900766386688932344[18] = 0;
   out_8900766386688932344[19] = 0;
   out_8900766386688932344[20] = 0;
   out_8900766386688932344[21] = 0;
   out_8900766386688932344[22] = 1;
   out_8900766386688932344[23] = 0;
   out_8900766386688932344[24] = 0;
   out_8900766386688932344[25] = 0;
   out_8900766386688932344[26] = 0;
   out_8900766386688932344[27] = 0;
   out_8900766386688932344[28] = 0;
   out_8900766386688932344[29] = 0;
   out_8900766386688932344[30] = 0;
   out_8900766386688932344[31] = 0;
   out_8900766386688932344[32] = 0;
   out_8900766386688932344[33] = 0;
   out_8900766386688932344[34] = 0;
   out_8900766386688932344[35] = 0;
   out_8900766386688932344[36] = 0;
   out_8900766386688932344[37] = 0;
   out_8900766386688932344[38] = 0;
   out_8900766386688932344[39] = 0;
   out_8900766386688932344[40] = 0;
   out_8900766386688932344[41] = 1;
   out_8900766386688932344[42] = 0;
   out_8900766386688932344[43] = 0;
   out_8900766386688932344[44] = 0;
   out_8900766386688932344[45] = 0;
   out_8900766386688932344[46] = 0;
   out_8900766386688932344[47] = 0;
   out_8900766386688932344[48] = 0;
   out_8900766386688932344[49] = 0;
   out_8900766386688932344[50] = 0;
   out_8900766386688932344[51] = 0;
   out_8900766386688932344[52] = 0;
   out_8900766386688932344[53] = 0;
}
void h_14(double *state, double *unused, double *out_1254666721235298923) {
   out_1254666721235298923[0] = state[6];
   out_1254666721235298923[1] = state[7];
   out_1254666721235298923[2] = state[8];
}
void H_14(double *state, double *unused, double *out_8149799355681780616) {
   out_8149799355681780616[0] = 0;
   out_8149799355681780616[1] = 0;
   out_8149799355681780616[2] = 0;
   out_8149799355681780616[3] = 0;
   out_8149799355681780616[4] = 0;
   out_8149799355681780616[5] = 0;
   out_8149799355681780616[6] = 1;
   out_8149799355681780616[7] = 0;
   out_8149799355681780616[8] = 0;
   out_8149799355681780616[9] = 0;
   out_8149799355681780616[10] = 0;
   out_8149799355681780616[11] = 0;
   out_8149799355681780616[12] = 0;
   out_8149799355681780616[13] = 0;
   out_8149799355681780616[14] = 0;
   out_8149799355681780616[15] = 0;
   out_8149799355681780616[16] = 0;
   out_8149799355681780616[17] = 0;
   out_8149799355681780616[18] = 0;
   out_8149799355681780616[19] = 0;
   out_8149799355681780616[20] = 0;
   out_8149799355681780616[21] = 0;
   out_8149799355681780616[22] = 0;
   out_8149799355681780616[23] = 0;
   out_8149799355681780616[24] = 0;
   out_8149799355681780616[25] = 1;
   out_8149799355681780616[26] = 0;
   out_8149799355681780616[27] = 0;
   out_8149799355681780616[28] = 0;
   out_8149799355681780616[29] = 0;
   out_8149799355681780616[30] = 0;
   out_8149799355681780616[31] = 0;
   out_8149799355681780616[32] = 0;
   out_8149799355681780616[33] = 0;
   out_8149799355681780616[34] = 0;
   out_8149799355681780616[35] = 0;
   out_8149799355681780616[36] = 0;
   out_8149799355681780616[37] = 0;
   out_8149799355681780616[38] = 0;
   out_8149799355681780616[39] = 0;
   out_8149799355681780616[40] = 0;
   out_8149799355681780616[41] = 0;
   out_8149799355681780616[42] = 0;
   out_8149799355681780616[43] = 0;
   out_8149799355681780616[44] = 1;
   out_8149799355681780616[45] = 0;
   out_8149799355681780616[46] = 0;
   out_8149799355681780616[47] = 0;
   out_8149799355681780616[48] = 0;
   out_8149799355681780616[49] = 0;
   out_8149799355681780616[50] = 0;
   out_8149799355681780616[51] = 0;
   out_8149799355681780616[52] = 0;
   out_8149799355681780616[53] = 0;
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
void pose_err_fun(double *nom_x, double *delta_x, double *out_8587424029422482613) {
  err_fun(nom_x, delta_x, out_8587424029422482613);
}
void pose_inv_err_fun(double *nom_x, double *true_x, double *out_8786163150320395038) {
  inv_err_fun(nom_x, true_x, out_8786163150320395038);
}
void pose_H_mod_fun(double *state, double *out_2404492370394702667) {
  H_mod_fun(state, out_2404492370394702667);
}
void pose_f_fun(double *state, double dt, double *out_442464745730678105) {
  f_fun(state,  dt, out_442464745730678105);
}
void pose_F_fun(double *state, double dt, double *out_68862599699564370) {
  F_fun(state,  dt, out_68862599699564370);
}
void pose_h_4(double *state, double *unused, double *out_6968799398651119641) {
  h_4(state, unused, out_6968799398651119641);
}
void pose_H_4(double *state, double *unused, double *out_6333703861688286471) {
  H_4(state, unused, out_6333703861688286471);
}
void pose_h_10(double *state, double *unused, double *out_5068008641526453532) {
  h_10(state, unused, out_5068008641526453532);
}
void pose_H_10(double *state, double *unused, double *out_3796470789070264043) {
  H_10(state, unused, out_3796470789070264043);
}
void pose_h_13(double *state, double *unused, double *out_1215417763549020361) {
  h_13(state, unused, out_1215417763549020361);
}
void pose_H_13(double *state, double *unused, double *out_8900766386688932344) {
  H_13(state, unused, out_8900766386688932344);
}
void pose_h_14(double *state, double *unused, double *out_1254666721235298923) {
  h_14(state, unused, out_1254666721235298923);
}
void pose_H_14(double *state, double *unused, double *out_8149799355681780616) {
  H_14(state, unused, out_8149799355681780616);
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
