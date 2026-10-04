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
void err_fun(double *nom_x, double *delta_x, double *out_3756367949668875994) {
   out_3756367949668875994[0] = delta_x[0] + nom_x[0];
   out_3756367949668875994[1] = delta_x[1] + nom_x[1];
   out_3756367949668875994[2] = delta_x[2] + nom_x[2];
   out_3756367949668875994[3] = delta_x[3] + nom_x[3];
   out_3756367949668875994[4] = delta_x[4] + nom_x[4];
   out_3756367949668875994[5] = delta_x[5] + nom_x[5];
   out_3756367949668875994[6] = delta_x[6] + nom_x[6];
   out_3756367949668875994[7] = delta_x[7] + nom_x[7];
   out_3756367949668875994[8] = delta_x[8] + nom_x[8];
   out_3756367949668875994[9] = delta_x[9] + nom_x[9];
   out_3756367949668875994[10] = delta_x[10] + nom_x[10];
   out_3756367949668875994[11] = delta_x[11] + nom_x[11];
   out_3756367949668875994[12] = delta_x[12] + nom_x[12];
   out_3756367949668875994[13] = delta_x[13] + nom_x[13];
   out_3756367949668875994[14] = delta_x[14] + nom_x[14];
   out_3756367949668875994[15] = delta_x[15] + nom_x[15];
   out_3756367949668875994[16] = delta_x[16] + nom_x[16];
   out_3756367949668875994[17] = delta_x[17] + nom_x[17];
}
void inv_err_fun(double *nom_x, double *true_x, double *out_649988038482950581) {
   out_649988038482950581[0] = -nom_x[0] + true_x[0];
   out_649988038482950581[1] = -nom_x[1] + true_x[1];
   out_649988038482950581[2] = -nom_x[2] + true_x[2];
   out_649988038482950581[3] = -nom_x[3] + true_x[3];
   out_649988038482950581[4] = -nom_x[4] + true_x[4];
   out_649988038482950581[5] = -nom_x[5] + true_x[5];
   out_649988038482950581[6] = -nom_x[6] + true_x[6];
   out_649988038482950581[7] = -nom_x[7] + true_x[7];
   out_649988038482950581[8] = -nom_x[8] + true_x[8];
   out_649988038482950581[9] = -nom_x[9] + true_x[9];
   out_649988038482950581[10] = -nom_x[10] + true_x[10];
   out_649988038482950581[11] = -nom_x[11] + true_x[11];
   out_649988038482950581[12] = -nom_x[12] + true_x[12];
   out_649988038482950581[13] = -nom_x[13] + true_x[13];
   out_649988038482950581[14] = -nom_x[14] + true_x[14];
   out_649988038482950581[15] = -nom_x[15] + true_x[15];
   out_649988038482950581[16] = -nom_x[16] + true_x[16];
   out_649988038482950581[17] = -nom_x[17] + true_x[17];
}
void H_mod_fun(double *state, double *out_7975290609355008534) {
   out_7975290609355008534[0] = 1.0;
   out_7975290609355008534[1] = 0.0;
   out_7975290609355008534[2] = 0.0;
   out_7975290609355008534[3] = 0.0;
   out_7975290609355008534[4] = 0.0;
   out_7975290609355008534[5] = 0.0;
   out_7975290609355008534[6] = 0.0;
   out_7975290609355008534[7] = 0.0;
   out_7975290609355008534[8] = 0.0;
   out_7975290609355008534[9] = 0.0;
   out_7975290609355008534[10] = 0.0;
   out_7975290609355008534[11] = 0.0;
   out_7975290609355008534[12] = 0.0;
   out_7975290609355008534[13] = 0.0;
   out_7975290609355008534[14] = 0.0;
   out_7975290609355008534[15] = 0.0;
   out_7975290609355008534[16] = 0.0;
   out_7975290609355008534[17] = 0.0;
   out_7975290609355008534[18] = 0.0;
   out_7975290609355008534[19] = 1.0;
   out_7975290609355008534[20] = 0.0;
   out_7975290609355008534[21] = 0.0;
   out_7975290609355008534[22] = 0.0;
   out_7975290609355008534[23] = 0.0;
   out_7975290609355008534[24] = 0.0;
   out_7975290609355008534[25] = 0.0;
   out_7975290609355008534[26] = 0.0;
   out_7975290609355008534[27] = 0.0;
   out_7975290609355008534[28] = 0.0;
   out_7975290609355008534[29] = 0.0;
   out_7975290609355008534[30] = 0.0;
   out_7975290609355008534[31] = 0.0;
   out_7975290609355008534[32] = 0.0;
   out_7975290609355008534[33] = 0.0;
   out_7975290609355008534[34] = 0.0;
   out_7975290609355008534[35] = 0.0;
   out_7975290609355008534[36] = 0.0;
   out_7975290609355008534[37] = 0.0;
   out_7975290609355008534[38] = 1.0;
   out_7975290609355008534[39] = 0.0;
   out_7975290609355008534[40] = 0.0;
   out_7975290609355008534[41] = 0.0;
   out_7975290609355008534[42] = 0.0;
   out_7975290609355008534[43] = 0.0;
   out_7975290609355008534[44] = 0.0;
   out_7975290609355008534[45] = 0.0;
   out_7975290609355008534[46] = 0.0;
   out_7975290609355008534[47] = 0.0;
   out_7975290609355008534[48] = 0.0;
   out_7975290609355008534[49] = 0.0;
   out_7975290609355008534[50] = 0.0;
   out_7975290609355008534[51] = 0.0;
   out_7975290609355008534[52] = 0.0;
   out_7975290609355008534[53] = 0.0;
   out_7975290609355008534[54] = 0.0;
   out_7975290609355008534[55] = 0.0;
   out_7975290609355008534[56] = 0.0;
   out_7975290609355008534[57] = 1.0;
   out_7975290609355008534[58] = 0.0;
   out_7975290609355008534[59] = 0.0;
   out_7975290609355008534[60] = 0.0;
   out_7975290609355008534[61] = 0.0;
   out_7975290609355008534[62] = 0.0;
   out_7975290609355008534[63] = 0.0;
   out_7975290609355008534[64] = 0.0;
   out_7975290609355008534[65] = 0.0;
   out_7975290609355008534[66] = 0.0;
   out_7975290609355008534[67] = 0.0;
   out_7975290609355008534[68] = 0.0;
   out_7975290609355008534[69] = 0.0;
   out_7975290609355008534[70] = 0.0;
   out_7975290609355008534[71] = 0.0;
   out_7975290609355008534[72] = 0.0;
   out_7975290609355008534[73] = 0.0;
   out_7975290609355008534[74] = 0.0;
   out_7975290609355008534[75] = 0.0;
   out_7975290609355008534[76] = 1.0;
   out_7975290609355008534[77] = 0.0;
   out_7975290609355008534[78] = 0.0;
   out_7975290609355008534[79] = 0.0;
   out_7975290609355008534[80] = 0.0;
   out_7975290609355008534[81] = 0.0;
   out_7975290609355008534[82] = 0.0;
   out_7975290609355008534[83] = 0.0;
   out_7975290609355008534[84] = 0.0;
   out_7975290609355008534[85] = 0.0;
   out_7975290609355008534[86] = 0.0;
   out_7975290609355008534[87] = 0.0;
   out_7975290609355008534[88] = 0.0;
   out_7975290609355008534[89] = 0.0;
   out_7975290609355008534[90] = 0.0;
   out_7975290609355008534[91] = 0.0;
   out_7975290609355008534[92] = 0.0;
   out_7975290609355008534[93] = 0.0;
   out_7975290609355008534[94] = 0.0;
   out_7975290609355008534[95] = 1.0;
   out_7975290609355008534[96] = 0.0;
   out_7975290609355008534[97] = 0.0;
   out_7975290609355008534[98] = 0.0;
   out_7975290609355008534[99] = 0.0;
   out_7975290609355008534[100] = 0.0;
   out_7975290609355008534[101] = 0.0;
   out_7975290609355008534[102] = 0.0;
   out_7975290609355008534[103] = 0.0;
   out_7975290609355008534[104] = 0.0;
   out_7975290609355008534[105] = 0.0;
   out_7975290609355008534[106] = 0.0;
   out_7975290609355008534[107] = 0.0;
   out_7975290609355008534[108] = 0.0;
   out_7975290609355008534[109] = 0.0;
   out_7975290609355008534[110] = 0.0;
   out_7975290609355008534[111] = 0.0;
   out_7975290609355008534[112] = 0.0;
   out_7975290609355008534[113] = 0.0;
   out_7975290609355008534[114] = 1.0;
   out_7975290609355008534[115] = 0.0;
   out_7975290609355008534[116] = 0.0;
   out_7975290609355008534[117] = 0.0;
   out_7975290609355008534[118] = 0.0;
   out_7975290609355008534[119] = 0.0;
   out_7975290609355008534[120] = 0.0;
   out_7975290609355008534[121] = 0.0;
   out_7975290609355008534[122] = 0.0;
   out_7975290609355008534[123] = 0.0;
   out_7975290609355008534[124] = 0.0;
   out_7975290609355008534[125] = 0.0;
   out_7975290609355008534[126] = 0.0;
   out_7975290609355008534[127] = 0.0;
   out_7975290609355008534[128] = 0.0;
   out_7975290609355008534[129] = 0.0;
   out_7975290609355008534[130] = 0.0;
   out_7975290609355008534[131] = 0.0;
   out_7975290609355008534[132] = 0.0;
   out_7975290609355008534[133] = 1.0;
   out_7975290609355008534[134] = 0.0;
   out_7975290609355008534[135] = 0.0;
   out_7975290609355008534[136] = 0.0;
   out_7975290609355008534[137] = 0.0;
   out_7975290609355008534[138] = 0.0;
   out_7975290609355008534[139] = 0.0;
   out_7975290609355008534[140] = 0.0;
   out_7975290609355008534[141] = 0.0;
   out_7975290609355008534[142] = 0.0;
   out_7975290609355008534[143] = 0.0;
   out_7975290609355008534[144] = 0.0;
   out_7975290609355008534[145] = 0.0;
   out_7975290609355008534[146] = 0.0;
   out_7975290609355008534[147] = 0.0;
   out_7975290609355008534[148] = 0.0;
   out_7975290609355008534[149] = 0.0;
   out_7975290609355008534[150] = 0.0;
   out_7975290609355008534[151] = 0.0;
   out_7975290609355008534[152] = 1.0;
   out_7975290609355008534[153] = 0.0;
   out_7975290609355008534[154] = 0.0;
   out_7975290609355008534[155] = 0.0;
   out_7975290609355008534[156] = 0.0;
   out_7975290609355008534[157] = 0.0;
   out_7975290609355008534[158] = 0.0;
   out_7975290609355008534[159] = 0.0;
   out_7975290609355008534[160] = 0.0;
   out_7975290609355008534[161] = 0.0;
   out_7975290609355008534[162] = 0.0;
   out_7975290609355008534[163] = 0.0;
   out_7975290609355008534[164] = 0.0;
   out_7975290609355008534[165] = 0.0;
   out_7975290609355008534[166] = 0.0;
   out_7975290609355008534[167] = 0.0;
   out_7975290609355008534[168] = 0.0;
   out_7975290609355008534[169] = 0.0;
   out_7975290609355008534[170] = 0.0;
   out_7975290609355008534[171] = 1.0;
   out_7975290609355008534[172] = 0.0;
   out_7975290609355008534[173] = 0.0;
   out_7975290609355008534[174] = 0.0;
   out_7975290609355008534[175] = 0.0;
   out_7975290609355008534[176] = 0.0;
   out_7975290609355008534[177] = 0.0;
   out_7975290609355008534[178] = 0.0;
   out_7975290609355008534[179] = 0.0;
   out_7975290609355008534[180] = 0.0;
   out_7975290609355008534[181] = 0.0;
   out_7975290609355008534[182] = 0.0;
   out_7975290609355008534[183] = 0.0;
   out_7975290609355008534[184] = 0.0;
   out_7975290609355008534[185] = 0.0;
   out_7975290609355008534[186] = 0.0;
   out_7975290609355008534[187] = 0.0;
   out_7975290609355008534[188] = 0.0;
   out_7975290609355008534[189] = 0.0;
   out_7975290609355008534[190] = 1.0;
   out_7975290609355008534[191] = 0.0;
   out_7975290609355008534[192] = 0.0;
   out_7975290609355008534[193] = 0.0;
   out_7975290609355008534[194] = 0.0;
   out_7975290609355008534[195] = 0.0;
   out_7975290609355008534[196] = 0.0;
   out_7975290609355008534[197] = 0.0;
   out_7975290609355008534[198] = 0.0;
   out_7975290609355008534[199] = 0.0;
   out_7975290609355008534[200] = 0.0;
   out_7975290609355008534[201] = 0.0;
   out_7975290609355008534[202] = 0.0;
   out_7975290609355008534[203] = 0.0;
   out_7975290609355008534[204] = 0.0;
   out_7975290609355008534[205] = 0.0;
   out_7975290609355008534[206] = 0.0;
   out_7975290609355008534[207] = 0.0;
   out_7975290609355008534[208] = 0.0;
   out_7975290609355008534[209] = 1.0;
   out_7975290609355008534[210] = 0.0;
   out_7975290609355008534[211] = 0.0;
   out_7975290609355008534[212] = 0.0;
   out_7975290609355008534[213] = 0.0;
   out_7975290609355008534[214] = 0.0;
   out_7975290609355008534[215] = 0.0;
   out_7975290609355008534[216] = 0.0;
   out_7975290609355008534[217] = 0.0;
   out_7975290609355008534[218] = 0.0;
   out_7975290609355008534[219] = 0.0;
   out_7975290609355008534[220] = 0.0;
   out_7975290609355008534[221] = 0.0;
   out_7975290609355008534[222] = 0.0;
   out_7975290609355008534[223] = 0.0;
   out_7975290609355008534[224] = 0.0;
   out_7975290609355008534[225] = 0.0;
   out_7975290609355008534[226] = 0.0;
   out_7975290609355008534[227] = 0.0;
   out_7975290609355008534[228] = 1.0;
   out_7975290609355008534[229] = 0.0;
   out_7975290609355008534[230] = 0.0;
   out_7975290609355008534[231] = 0.0;
   out_7975290609355008534[232] = 0.0;
   out_7975290609355008534[233] = 0.0;
   out_7975290609355008534[234] = 0.0;
   out_7975290609355008534[235] = 0.0;
   out_7975290609355008534[236] = 0.0;
   out_7975290609355008534[237] = 0.0;
   out_7975290609355008534[238] = 0.0;
   out_7975290609355008534[239] = 0.0;
   out_7975290609355008534[240] = 0.0;
   out_7975290609355008534[241] = 0.0;
   out_7975290609355008534[242] = 0.0;
   out_7975290609355008534[243] = 0.0;
   out_7975290609355008534[244] = 0.0;
   out_7975290609355008534[245] = 0.0;
   out_7975290609355008534[246] = 0.0;
   out_7975290609355008534[247] = 1.0;
   out_7975290609355008534[248] = 0.0;
   out_7975290609355008534[249] = 0.0;
   out_7975290609355008534[250] = 0.0;
   out_7975290609355008534[251] = 0.0;
   out_7975290609355008534[252] = 0.0;
   out_7975290609355008534[253] = 0.0;
   out_7975290609355008534[254] = 0.0;
   out_7975290609355008534[255] = 0.0;
   out_7975290609355008534[256] = 0.0;
   out_7975290609355008534[257] = 0.0;
   out_7975290609355008534[258] = 0.0;
   out_7975290609355008534[259] = 0.0;
   out_7975290609355008534[260] = 0.0;
   out_7975290609355008534[261] = 0.0;
   out_7975290609355008534[262] = 0.0;
   out_7975290609355008534[263] = 0.0;
   out_7975290609355008534[264] = 0.0;
   out_7975290609355008534[265] = 0.0;
   out_7975290609355008534[266] = 1.0;
   out_7975290609355008534[267] = 0.0;
   out_7975290609355008534[268] = 0.0;
   out_7975290609355008534[269] = 0.0;
   out_7975290609355008534[270] = 0.0;
   out_7975290609355008534[271] = 0.0;
   out_7975290609355008534[272] = 0.0;
   out_7975290609355008534[273] = 0.0;
   out_7975290609355008534[274] = 0.0;
   out_7975290609355008534[275] = 0.0;
   out_7975290609355008534[276] = 0.0;
   out_7975290609355008534[277] = 0.0;
   out_7975290609355008534[278] = 0.0;
   out_7975290609355008534[279] = 0.0;
   out_7975290609355008534[280] = 0.0;
   out_7975290609355008534[281] = 0.0;
   out_7975290609355008534[282] = 0.0;
   out_7975290609355008534[283] = 0.0;
   out_7975290609355008534[284] = 0.0;
   out_7975290609355008534[285] = 1.0;
   out_7975290609355008534[286] = 0.0;
   out_7975290609355008534[287] = 0.0;
   out_7975290609355008534[288] = 0.0;
   out_7975290609355008534[289] = 0.0;
   out_7975290609355008534[290] = 0.0;
   out_7975290609355008534[291] = 0.0;
   out_7975290609355008534[292] = 0.0;
   out_7975290609355008534[293] = 0.0;
   out_7975290609355008534[294] = 0.0;
   out_7975290609355008534[295] = 0.0;
   out_7975290609355008534[296] = 0.0;
   out_7975290609355008534[297] = 0.0;
   out_7975290609355008534[298] = 0.0;
   out_7975290609355008534[299] = 0.0;
   out_7975290609355008534[300] = 0.0;
   out_7975290609355008534[301] = 0.0;
   out_7975290609355008534[302] = 0.0;
   out_7975290609355008534[303] = 0.0;
   out_7975290609355008534[304] = 1.0;
   out_7975290609355008534[305] = 0.0;
   out_7975290609355008534[306] = 0.0;
   out_7975290609355008534[307] = 0.0;
   out_7975290609355008534[308] = 0.0;
   out_7975290609355008534[309] = 0.0;
   out_7975290609355008534[310] = 0.0;
   out_7975290609355008534[311] = 0.0;
   out_7975290609355008534[312] = 0.0;
   out_7975290609355008534[313] = 0.0;
   out_7975290609355008534[314] = 0.0;
   out_7975290609355008534[315] = 0.0;
   out_7975290609355008534[316] = 0.0;
   out_7975290609355008534[317] = 0.0;
   out_7975290609355008534[318] = 0.0;
   out_7975290609355008534[319] = 0.0;
   out_7975290609355008534[320] = 0.0;
   out_7975290609355008534[321] = 0.0;
   out_7975290609355008534[322] = 0.0;
   out_7975290609355008534[323] = 1.0;
}
void f_fun(double *state, double dt, double *out_3747162810741447441) {
   out_3747162810741447441[0] = atan2((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), -(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]));
   out_3747162810741447441[1] = asin(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]));
   out_3747162810741447441[2] = atan2(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), -(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]));
   out_3747162810741447441[3] = dt*state[12] + state[3];
   out_3747162810741447441[4] = dt*state[13] + state[4];
   out_3747162810741447441[5] = dt*state[14] + state[5];
   out_3747162810741447441[6] = state[6];
   out_3747162810741447441[7] = state[7];
   out_3747162810741447441[8] = state[8];
   out_3747162810741447441[9] = state[9];
   out_3747162810741447441[10] = state[10];
   out_3747162810741447441[11] = state[11];
   out_3747162810741447441[12] = state[12];
   out_3747162810741447441[13] = state[13];
   out_3747162810741447441[14] = state[14];
   out_3747162810741447441[15] = state[15];
   out_3747162810741447441[16] = state[16];
   out_3747162810741447441[17] = state[17];
}
void F_fun(double *state, double dt, double *out_4622144854708215450) {
   out_4622144854708215450[0] = ((-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*cos(state[0])*cos(state[1]) - sin(state[0])*cos(dt*state[6])*cos(dt*state[7])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + ((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*cos(state[0])*cos(state[1]) - sin(dt*state[6])*sin(state[0])*cos(dt*state[7])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_4622144854708215450[1] = ((-sin(dt*state[6])*sin(dt*state[8]) - sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*cos(state[1]) - (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*sin(state[1]) - sin(state[1])*cos(dt*state[6])*cos(dt*state[7])*cos(state[0]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*sin(state[1]) + (-sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) + sin(dt*state[8])*cos(dt*state[6]))*cos(state[1]) - sin(dt*state[6])*sin(state[1])*cos(dt*state[7])*cos(state[0]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_4622144854708215450[2] = 0;
   out_4622144854708215450[3] = 0;
   out_4622144854708215450[4] = 0;
   out_4622144854708215450[5] = 0;
   out_4622144854708215450[6] = (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(dt*cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*sin(dt*state[8]) - dt*sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-dt*sin(dt*state[6])*cos(dt*state[8]) + dt*sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) - dt*cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (dt*sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_4622144854708215450[7] = (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[6])*sin(dt*state[7])*cos(state[0])*cos(state[1]) + dt*sin(dt*state[6])*sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) - dt*sin(dt*state[6])*sin(state[1])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[7])*cos(dt*state[6])*cos(state[0])*cos(state[1]) + dt*sin(dt*state[8])*sin(state[0])*cos(dt*state[6])*cos(dt*state[7])*cos(state[1]) - dt*sin(state[1])*cos(dt*state[6])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_4622144854708215450[8] = ((dt*sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + dt*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (dt*sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + ((dt*sin(dt*state[6])*sin(dt*state[8]) + dt*sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*cos(dt*state[8]) + dt*sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_4622144854708215450[9] = 0;
   out_4622144854708215450[10] = 0;
   out_4622144854708215450[11] = 0;
   out_4622144854708215450[12] = 0;
   out_4622144854708215450[13] = 0;
   out_4622144854708215450[14] = 0;
   out_4622144854708215450[15] = 0;
   out_4622144854708215450[16] = 0;
   out_4622144854708215450[17] = 0;
   out_4622144854708215450[18] = (-sin(dt*state[7])*sin(state[0])*cos(state[1]) - sin(dt*state[8])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_4622144854708215450[19] = (-sin(dt*state[7])*sin(state[1])*cos(state[0]) + sin(dt*state[8])*sin(state[0])*sin(state[1])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_4622144854708215450[20] = 0;
   out_4622144854708215450[21] = 0;
   out_4622144854708215450[22] = 0;
   out_4622144854708215450[23] = 0;
   out_4622144854708215450[24] = 0;
   out_4622144854708215450[25] = (dt*sin(dt*state[7])*sin(dt*state[8])*sin(state[0])*cos(state[1]) - dt*sin(dt*state[7])*sin(state[1])*cos(dt*state[8]) + dt*cos(dt*state[7])*cos(state[0])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_4622144854708215450[26] = (-dt*sin(dt*state[8])*sin(state[1])*cos(dt*state[7]) - dt*sin(state[0])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_4622144854708215450[27] = 0;
   out_4622144854708215450[28] = 0;
   out_4622144854708215450[29] = 0;
   out_4622144854708215450[30] = 0;
   out_4622144854708215450[31] = 0;
   out_4622144854708215450[32] = 0;
   out_4622144854708215450[33] = 0;
   out_4622144854708215450[34] = 0;
   out_4622144854708215450[35] = 0;
   out_4622144854708215450[36] = ((sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[7]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[7]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_4622144854708215450[37] = (-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(-sin(dt*state[7])*sin(state[2])*cos(state[0])*cos(state[1]) + sin(dt*state[8])*sin(state[0])*sin(state[2])*cos(dt*state[7])*cos(state[1]) - sin(state[1])*sin(state[2])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*(-sin(dt*state[7])*cos(state[0])*cos(state[1])*cos(state[2]) + sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1])*cos(state[2]) - sin(state[1])*cos(dt*state[7])*cos(dt*state[8])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_4622144854708215450[38] = ((-sin(state[0])*sin(state[2]) - sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (-sin(state[0])*sin(state[1])*sin(state[2]) - cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_4622144854708215450[39] = 0;
   out_4622144854708215450[40] = 0;
   out_4622144854708215450[41] = 0;
   out_4622144854708215450[42] = 0;
   out_4622144854708215450[43] = (-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(dt*(sin(state[0])*cos(state[2]) - sin(state[1])*sin(state[2])*cos(state[0]))*cos(dt*state[7]) - dt*(sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[7])*sin(dt*state[8]) - dt*sin(dt*state[7])*sin(state[2])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*(dt*(-sin(state[0])*sin(state[2]) - sin(state[1])*cos(state[0])*cos(state[2]))*cos(dt*state[7]) - dt*(sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[7])*sin(dt*state[8]) - dt*sin(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_4622144854708215450[44] = (dt*(sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*cos(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*sin(state[2])*cos(dt*state[7])*cos(state[1]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + (dt*(sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*cos(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[7])*cos(state[1])*cos(state[2]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_4622144854708215450[45] = 0;
   out_4622144854708215450[46] = 0;
   out_4622144854708215450[47] = 0;
   out_4622144854708215450[48] = 0;
   out_4622144854708215450[49] = 0;
   out_4622144854708215450[50] = 0;
   out_4622144854708215450[51] = 0;
   out_4622144854708215450[52] = 0;
   out_4622144854708215450[53] = 0;
   out_4622144854708215450[54] = 0;
   out_4622144854708215450[55] = 0;
   out_4622144854708215450[56] = 0;
   out_4622144854708215450[57] = 1;
   out_4622144854708215450[58] = 0;
   out_4622144854708215450[59] = 0;
   out_4622144854708215450[60] = 0;
   out_4622144854708215450[61] = 0;
   out_4622144854708215450[62] = 0;
   out_4622144854708215450[63] = 0;
   out_4622144854708215450[64] = 0;
   out_4622144854708215450[65] = 0;
   out_4622144854708215450[66] = dt;
   out_4622144854708215450[67] = 0;
   out_4622144854708215450[68] = 0;
   out_4622144854708215450[69] = 0;
   out_4622144854708215450[70] = 0;
   out_4622144854708215450[71] = 0;
   out_4622144854708215450[72] = 0;
   out_4622144854708215450[73] = 0;
   out_4622144854708215450[74] = 0;
   out_4622144854708215450[75] = 0;
   out_4622144854708215450[76] = 1;
   out_4622144854708215450[77] = 0;
   out_4622144854708215450[78] = 0;
   out_4622144854708215450[79] = 0;
   out_4622144854708215450[80] = 0;
   out_4622144854708215450[81] = 0;
   out_4622144854708215450[82] = 0;
   out_4622144854708215450[83] = 0;
   out_4622144854708215450[84] = 0;
   out_4622144854708215450[85] = dt;
   out_4622144854708215450[86] = 0;
   out_4622144854708215450[87] = 0;
   out_4622144854708215450[88] = 0;
   out_4622144854708215450[89] = 0;
   out_4622144854708215450[90] = 0;
   out_4622144854708215450[91] = 0;
   out_4622144854708215450[92] = 0;
   out_4622144854708215450[93] = 0;
   out_4622144854708215450[94] = 0;
   out_4622144854708215450[95] = 1;
   out_4622144854708215450[96] = 0;
   out_4622144854708215450[97] = 0;
   out_4622144854708215450[98] = 0;
   out_4622144854708215450[99] = 0;
   out_4622144854708215450[100] = 0;
   out_4622144854708215450[101] = 0;
   out_4622144854708215450[102] = 0;
   out_4622144854708215450[103] = 0;
   out_4622144854708215450[104] = dt;
   out_4622144854708215450[105] = 0;
   out_4622144854708215450[106] = 0;
   out_4622144854708215450[107] = 0;
   out_4622144854708215450[108] = 0;
   out_4622144854708215450[109] = 0;
   out_4622144854708215450[110] = 0;
   out_4622144854708215450[111] = 0;
   out_4622144854708215450[112] = 0;
   out_4622144854708215450[113] = 0;
   out_4622144854708215450[114] = 1;
   out_4622144854708215450[115] = 0;
   out_4622144854708215450[116] = 0;
   out_4622144854708215450[117] = 0;
   out_4622144854708215450[118] = 0;
   out_4622144854708215450[119] = 0;
   out_4622144854708215450[120] = 0;
   out_4622144854708215450[121] = 0;
   out_4622144854708215450[122] = 0;
   out_4622144854708215450[123] = 0;
   out_4622144854708215450[124] = 0;
   out_4622144854708215450[125] = 0;
   out_4622144854708215450[126] = 0;
   out_4622144854708215450[127] = 0;
   out_4622144854708215450[128] = 0;
   out_4622144854708215450[129] = 0;
   out_4622144854708215450[130] = 0;
   out_4622144854708215450[131] = 0;
   out_4622144854708215450[132] = 0;
   out_4622144854708215450[133] = 1;
   out_4622144854708215450[134] = 0;
   out_4622144854708215450[135] = 0;
   out_4622144854708215450[136] = 0;
   out_4622144854708215450[137] = 0;
   out_4622144854708215450[138] = 0;
   out_4622144854708215450[139] = 0;
   out_4622144854708215450[140] = 0;
   out_4622144854708215450[141] = 0;
   out_4622144854708215450[142] = 0;
   out_4622144854708215450[143] = 0;
   out_4622144854708215450[144] = 0;
   out_4622144854708215450[145] = 0;
   out_4622144854708215450[146] = 0;
   out_4622144854708215450[147] = 0;
   out_4622144854708215450[148] = 0;
   out_4622144854708215450[149] = 0;
   out_4622144854708215450[150] = 0;
   out_4622144854708215450[151] = 0;
   out_4622144854708215450[152] = 1;
   out_4622144854708215450[153] = 0;
   out_4622144854708215450[154] = 0;
   out_4622144854708215450[155] = 0;
   out_4622144854708215450[156] = 0;
   out_4622144854708215450[157] = 0;
   out_4622144854708215450[158] = 0;
   out_4622144854708215450[159] = 0;
   out_4622144854708215450[160] = 0;
   out_4622144854708215450[161] = 0;
   out_4622144854708215450[162] = 0;
   out_4622144854708215450[163] = 0;
   out_4622144854708215450[164] = 0;
   out_4622144854708215450[165] = 0;
   out_4622144854708215450[166] = 0;
   out_4622144854708215450[167] = 0;
   out_4622144854708215450[168] = 0;
   out_4622144854708215450[169] = 0;
   out_4622144854708215450[170] = 0;
   out_4622144854708215450[171] = 1;
   out_4622144854708215450[172] = 0;
   out_4622144854708215450[173] = 0;
   out_4622144854708215450[174] = 0;
   out_4622144854708215450[175] = 0;
   out_4622144854708215450[176] = 0;
   out_4622144854708215450[177] = 0;
   out_4622144854708215450[178] = 0;
   out_4622144854708215450[179] = 0;
   out_4622144854708215450[180] = 0;
   out_4622144854708215450[181] = 0;
   out_4622144854708215450[182] = 0;
   out_4622144854708215450[183] = 0;
   out_4622144854708215450[184] = 0;
   out_4622144854708215450[185] = 0;
   out_4622144854708215450[186] = 0;
   out_4622144854708215450[187] = 0;
   out_4622144854708215450[188] = 0;
   out_4622144854708215450[189] = 0;
   out_4622144854708215450[190] = 1;
   out_4622144854708215450[191] = 0;
   out_4622144854708215450[192] = 0;
   out_4622144854708215450[193] = 0;
   out_4622144854708215450[194] = 0;
   out_4622144854708215450[195] = 0;
   out_4622144854708215450[196] = 0;
   out_4622144854708215450[197] = 0;
   out_4622144854708215450[198] = 0;
   out_4622144854708215450[199] = 0;
   out_4622144854708215450[200] = 0;
   out_4622144854708215450[201] = 0;
   out_4622144854708215450[202] = 0;
   out_4622144854708215450[203] = 0;
   out_4622144854708215450[204] = 0;
   out_4622144854708215450[205] = 0;
   out_4622144854708215450[206] = 0;
   out_4622144854708215450[207] = 0;
   out_4622144854708215450[208] = 0;
   out_4622144854708215450[209] = 1;
   out_4622144854708215450[210] = 0;
   out_4622144854708215450[211] = 0;
   out_4622144854708215450[212] = 0;
   out_4622144854708215450[213] = 0;
   out_4622144854708215450[214] = 0;
   out_4622144854708215450[215] = 0;
   out_4622144854708215450[216] = 0;
   out_4622144854708215450[217] = 0;
   out_4622144854708215450[218] = 0;
   out_4622144854708215450[219] = 0;
   out_4622144854708215450[220] = 0;
   out_4622144854708215450[221] = 0;
   out_4622144854708215450[222] = 0;
   out_4622144854708215450[223] = 0;
   out_4622144854708215450[224] = 0;
   out_4622144854708215450[225] = 0;
   out_4622144854708215450[226] = 0;
   out_4622144854708215450[227] = 0;
   out_4622144854708215450[228] = 1;
   out_4622144854708215450[229] = 0;
   out_4622144854708215450[230] = 0;
   out_4622144854708215450[231] = 0;
   out_4622144854708215450[232] = 0;
   out_4622144854708215450[233] = 0;
   out_4622144854708215450[234] = 0;
   out_4622144854708215450[235] = 0;
   out_4622144854708215450[236] = 0;
   out_4622144854708215450[237] = 0;
   out_4622144854708215450[238] = 0;
   out_4622144854708215450[239] = 0;
   out_4622144854708215450[240] = 0;
   out_4622144854708215450[241] = 0;
   out_4622144854708215450[242] = 0;
   out_4622144854708215450[243] = 0;
   out_4622144854708215450[244] = 0;
   out_4622144854708215450[245] = 0;
   out_4622144854708215450[246] = 0;
   out_4622144854708215450[247] = 1;
   out_4622144854708215450[248] = 0;
   out_4622144854708215450[249] = 0;
   out_4622144854708215450[250] = 0;
   out_4622144854708215450[251] = 0;
   out_4622144854708215450[252] = 0;
   out_4622144854708215450[253] = 0;
   out_4622144854708215450[254] = 0;
   out_4622144854708215450[255] = 0;
   out_4622144854708215450[256] = 0;
   out_4622144854708215450[257] = 0;
   out_4622144854708215450[258] = 0;
   out_4622144854708215450[259] = 0;
   out_4622144854708215450[260] = 0;
   out_4622144854708215450[261] = 0;
   out_4622144854708215450[262] = 0;
   out_4622144854708215450[263] = 0;
   out_4622144854708215450[264] = 0;
   out_4622144854708215450[265] = 0;
   out_4622144854708215450[266] = 1;
   out_4622144854708215450[267] = 0;
   out_4622144854708215450[268] = 0;
   out_4622144854708215450[269] = 0;
   out_4622144854708215450[270] = 0;
   out_4622144854708215450[271] = 0;
   out_4622144854708215450[272] = 0;
   out_4622144854708215450[273] = 0;
   out_4622144854708215450[274] = 0;
   out_4622144854708215450[275] = 0;
   out_4622144854708215450[276] = 0;
   out_4622144854708215450[277] = 0;
   out_4622144854708215450[278] = 0;
   out_4622144854708215450[279] = 0;
   out_4622144854708215450[280] = 0;
   out_4622144854708215450[281] = 0;
   out_4622144854708215450[282] = 0;
   out_4622144854708215450[283] = 0;
   out_4622144854708215450[284] = 0;
   out_4622144854708215450[285] = 1;
   out_4622144854708215450[286] = 0;
   out_4622144854708215450[287] = 0;
   out_4622144854708215450[288] = 0;
   out_4622144854708215450[289] = 0;
   out_4622144854708215450[290] = 0;
   out_4622144854708215450[291] = 0;
   out_4622144854708215450[292] = 0;
   out_4622144854708215450[293] = 0;
   out_4622144854708215450[294] = 0;
   out_4622144854708215450[295] = 0;
   out_4622144854708215450[296] = 0;
   out_4622144854708215450[297] = 0;
   out_4622144854708215450[298] = 0;
   out_4622144854708215450[299] = 0;
   out_4622144854708215450[300] = 0;
   out_4622144854708215450[301] = 0;
   out_4622144854708215450[302] = 0;
   out_4622144854708215450[303] = 0;
   out_4622144854708215450[304] = 1;
   out_4622144854708215450[305] = 0;
   out_4622144854708215450[306] = 0;
   out_4622144854708215450[307] = 0;
   out_4622144854708215450[308] = 0;
   out_4622144854708215450[309] = 0;
   out_4622144854708215450[310] = 0;
   out_4622144854708215450[311] = 0;
   out_4622144854708215450[312] = 0;
   out_4622144854708215450[313] = 0;
   out_4622144854708215450[314] = 0;
   out_4622144854708215450[315] = 0;
   out_4622144854708215450[316] = 0;
   out_4622144854708215450[317] = 0;
   out_4622144854708215450[318] = 0;
   out_4622144854708215450[319] = 0;
   out_4622144854708215450[320] = 0;
   out_4622144854708215450[321] = 0;
   out_4622144854708215450[322] = 0;
   out_4622144854708215450[323] = 1;
}
void h_4(double *state, double *unused, double *out_2034104138300694595) {
   out_2034104138300694595[0] = state[6] + state[9];
   out_2034104138300694595[1] = state[7] + state[10];
   out_2034104138300694595[2] = state[8] + state[11];
}
void H_4(double *state, double *unused, double *out_7221129607300295927) {
   out_7221129607300295927[0] = 0;
   out_7221129607300295927[1] = 0;
   out_7221129607300295927[2] = 0;
   out_7221129607300295927[3] = 0;
   out_7221129607300295927[4] = 0;
   out_7221129607300295927[5] = 0;
   out_7221129607300295927[6] = 1;
   out_7221129607300295927[7] = 0;
   out_7221129607300295927[8] = 0;
   out_7221129607300295927[9] = 1;
   out_7221129607300295927[10] = 0;
   out_7221129607300295927[11] = 0;
   out_7221129607300295927[12] = 0;
   out_7221129607300295927[13] = 0;
   out_7221129607300295927[14] = 0;
   out_7221129607300295927[15] = 0;
   out_7221129607300295927[16] = 0;
   out_7221129607300295927[17] = 0;
   out_7221129607300295927[18] = 0;
   out_7221129607300295927[19] = 0;
   out_7221129607300295927[20] = 0;
   out_7221129607300295927[21] = 0;
   out_7221129607300295927[22] = 0;
   out_7221129607300295927[23] = 0;
   out_7221129607300295927[24] = 0;
   out_7221129607300295927[25] = 1;
   out_7221129607300295927[26] = 0;
   out_7221129607300295927[27] = 0;
   out_7221129607300295927[28] = 1;
   out_7221129607300295927[29] = 0;
   out_7221129607300295927[30] = 0;
   out_7221129607300295927[31] = 0;
   out_7221129607300295927[32] = 0;
   out_7221129607300295927[33] = 0;
   out_7221129607300295927[34] = 0;
   out_7221129607300295927[35] = 0;
   out_7221129607300295927[36] = 0;
   out_7221129607300295927[37] = 0;
   out_7221129607300295927[38] = 0;
   out_7221129607300295927[39] = 0;
   out_7221129607300295927[40] = 0;
   out_7221129607300295927[41] = 0;
   out_7221129607300295927[42] = 0;
   out_7221129607300295927[43] = 0;
   out_7221129607300295927[44] = 1;
   out_7221129607300295927[45] = 0;
   out_7221129607300295927[46] = 0;
   out_7221129607300295927[47] = 1;
   out_7221129607300295927[48] = 0;
   out_7221129607300295927[49] = 0;
   out_7221129607300295927[50] = 0;
   out_7221129607300295927[51] = 0;
   out_7221129607300295927[52] = 0;
   out_7221129607300295927[53] = 0;
}
void h_10(double *state, double *unused, double *out_1561728162162688074) {
   out_1561728162162688074[0] = 9.8100000000000005*sin(state[1]) - state[4]*state[8] + state[5]*state[7] + state[12] + state[15];
   out_1561728162162688074[1] = -9.8100000000000005*sin(state[0])*cos(state[1]) + state[3]*state[8] - state[5]*state[6] + state[13] + state[16];
   out_1561728162162688074[2] = -9.8100000000000005*cos(state[0])*cos(state[1]) - state[3]*state[7] + state[4]*state[6] + state[14] + state[17];
}
void H_10(double *state, double *unused, double *out_8343161513752116907) {
   out_8343161513752116907[0] = 0;
   out_8343161513752116907[1] = 9.8100000000000005*cos(state[1]);
   out_8343161513752116907[2] = 0;
   out_8343161513752116907[3] = 0;
   out_8343161513752116907[4] = -state[8];
   out_8343161513752116907[5] = state[7];
   out_8343161513752116907[6] = 0;
   out_8343161513752116907[7] = state[5];
   out_8343161513752116907[8] = -state[4];
   out_8343161513752116907[9] = 0;
   out_8343161513752116907[10] = 0;
   out_8343161513752116907[11] = 0;
   out_8343161513752116907[12] = 1;
   out_8343161513752116907[13] = 0;
   out_8343161513752116907[14] = 0;
   out_8343161513752116907[15] = 1;
   out_8343161513752116907[16] = 0;
   out_8343161513752116907[17] = 0;
   out_8343161513752116907[18] = -9.8100000000000005*cos(state[0])*cos(state[1]);
   out_8343161513752116907[19] = 9.8100000000000005*sin(state[0])*sin(state[1]);
   out_8343161513752116907[20] = 0;
   out_8343161513752116907[21] = state[8];
   out_8343161513752116907[22] = 0;
   out_8343161513752116907[23] = -state[6];
   out_8343161513752116907[24] = -state[5];
   out_8343161513752116907[25] = 0;
   out_8343161513752116907[26] = state[3];
   out_8343161513752116907[27] = 0;
   out_8343161513752116907[28] = 0;
   out_8343161513752116907[29] = 0;
   out_8343161513752116907[30] = 0;
   out_8343161513752116907[31] = 1;
   out_8343161513752116907[32] = 0;
   out_8343161513752116907[33] = 0;
   out_8343161513752116907[34] = 1;
   out_8343161513752116907[35] = 0;
   out_8343161513752116907[36] = 9.8100000000000005*sin(state[0])*cos(state[1]);
   out_8343161513752116907[37] = 9.8100000000000005*sin(state[1])*cos(state[0]);
   out_8343161513752116907[38] = 0;
   out_8343161513752116907[39] = -state[7];
   out_8343161513752116907[40] = state[6];
   out_8343161513752116907[41] = 0;
   out_8343161513752116907[42] = state[4];
   out_8343161513752116907[43] = -state[3];
   out_8343161513752116907[44] = 0;
   out_8343161513752116907[45] = 0;
   out_8343161513752116907[46] = 0;
   out_8343161513752116907[47] = 0;
   out_8343161513752116907[48] = 0;
   out_8343161513752116907[49] = 0;
   out_8343161513752116907[50] = 1;
   out_8343161513752116907[51] = 0;
   out_8343161513752116907[52] = 0;
   out_8343161513752116907[53] = 1;
}
void h_13(double *state, double *unused, double *out_425557749313340936) {
   out_425557749313340936[0] = state[3];
   out_425557749313340936[1] = state[4];
   out_425557749313340936[2] = state[5];
}
void H_13(double *state, double *unused, double *out_389501601016405002) {
   out_389501601016405002[0] = 0;
   out_389501601016405002[1] = 0;
   out_389501601016405002[2] = 0;
   out_389501601016405002[3] = 1;
   out_389501601016405002[4] = 0;
   out_389501601016405002[5] = 0;
   out_389501601016405002[6] = 0;
   out_389501601016405002[7] = 0;
   out_389501601016405002[8] = 0;
   out_389501601016405002[9] = 0;
   out_389501601016405002[10] = 0;
   out_389501601016405002[11] = 0;
   out_389501601016405002[12] = 0;
   out_389501601016405002[13] = 0;
   out_389501601016405002[14] = 0;
   out_389501601016405002[15] = 0;
   out_389501601016405002[16] = 0;
   out_389501601016405002[17] = 0;
   out_389501601016405002[18] = 0;
   out_389501601016405002[19] = 0;
   out_389501601016405002[20] = 0;
   out_389501601016405002[21] = 0;
   out_389501601016405002[22] = 1;
   out_389501601016405002[23] = 0;
   out_389501601016405002[24] = 0;
   out_389501601016405002[25] = 0;
   out_389501601016405002[26] = 0;
   out_389501601016405002[27] = 0;
   out_389501601016405002[28] = 0;
   out_389501601016405002[29] = 0;
   out_389501601016405002[30] = 0;
   out_389501601016405002[31] = 0;
   out_389501601016405002[32] = 0;
   out_389501601016405002[33] = 0;
   out_389501601016405002[34] = 0;
   out_389501601016405002[35] = 0;
   out_389501601016405002[36] = 0;
   out_389501601016405002[37] = 0;
   out_389501601016405002[38] = 0;
   out_389501601016405002[39] = 0;
   out_389501601016405002[40] = 0;
   out_389501601016405002[41] = 1;
   out_389501601016405002[42] = 0;
   out_389501601016405002[43] = 0;
   out_389501601016405002[44] = 0;
   out_389501601016405002[45] = 0;
   out_389501601016405002[46] = 0;
   out_389501601016405002[47] = 0;
   out_389501601016405002[48] = 0;
   out_389501601016405002[49] = 0;
   out_389501601016405002[50] = 0;
   out_389501601016405002[51] = 0;
   out_389501601016405002[52] = 0;
   out_389501601016405002[53] = 0;
}
void h_14(double *state, double *unused, double *out_6807261625183760659) {
   out_6807261625183760659[0] = state[6];
   out_6807261625183760659[1] = state[7];
   out_6807261625183760659[2] = state[8];
}
void H_14(double *state, double *unused, double *out_3257888750960811398) {
   out_3257888750960811398[0] = 0;
   out_3257888750960811398[1] = 0;
   out_3257888750960811398[2] = 0;
   out_3257888750960811398[3] = 0;
   out_3257888750960811398[4] = 0;
   out_3257888750960811398[5] = 0;
   out_3257888750960811398[6] = 1;
   out_3257888750960811398[7] = 0;
   out_3257888750960811398[8] = 0;
   out_3257888750960811398[9] = 0;
   out_3257888750960811398[10] = 0;
   out_3257888750960811398[11] = 0;
   out_3257888750960811398[12] = 0;
   out_3257888750960811398[13] = 0;
   out_3257888750960811398[14] = 0;
   out_3257888750960811398[15] = 0;
   out_3257888750960811398[16] = 0;
   out_3257888750960811398[17] = 0;
   out_3257888750960811398[18] = 0;
   out_3257888750960811398[19] = 0;
   out_3257888750960811398[20] = 0;
   out_3257888750960811398[21] = 0;
   out_3257888750960811398[22] = 0;
   out_3257888750960811398[23] = 0;
   out_3257888750960811398[24] = 0;
   out_3257888750960811398[25] = 1;
   out_3257888750960811398[26] = 0;
   out_3257888750960811398[27] = 0;
   out_3257888750960811398[28] = 0;
   out_3257888750960811398[29] = 0;
   out_3257888750960811398[30] = 0;
   out_3257888750960811398[31] = 0;
   out_3257888750960811398[32] = 0;
   out_3257888750960811398[33] = 0;
   out_3257888750960811398[34] = 0;
   out_3257888750960811398[35] = 0;
   out_3257888750960811398[36] = 0;
   out_3257888750960811398[37] = 0;
   out_3257888750960811398[38] = 0;
   out_3257888750960811398[39] = 0;
   out_3257888750960811398[40] = 0;
   out_3257888750960811398[41] = 0;
   out_3257888750960811398[42] = 0;
   out_3257888750960811398[43] = 0;
   out_3257888750960811398[44] = 1;
   out_3257888750960811398[45] = 0;
   out_3257888750960811398[46] = 0;
   out_3257888750960811398[47] = 0;
   out_3257888750960811398[48] = 0;
   out_3257888750960811398[49] = 0;
   out_3257888750960811398[50] = 0;
   out_3257888750960811398[51] = 0;
   out_3257888750960811398[52] = 0;
   out_3257888750960811398[53] = 0;
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
void pose_err_fun(double *nom_x, double *delta_x, double *out_3756367949668875994) {
  err_fun(nom_x, delta_x, out_3756367949668875994);
}
void pose_inv_err_fun(double *nom_x, double *true_x, double *out_649988038482950581) {
  inv_err_fun(nom_x, true_x, out_649988038482950581);
}
void pose_H_mod_fun(double *state, double *out_7975290609355008534) {
  H_mod_fun(state, out_7975290609355008534);
}
void pose_f_fun(double *state, double dt, double *out_3747162810741447441) {
  f_fun(state,  dt, out_3747162810741447441);
}
void pose_F_fun(double *state, double dt, double *out_4622144854708215450) {
  F_fun(state,  dt, out_4622144854708215450);
}
void pose_h_4(double *state, double *unused, double *out_2034104138300694595) {
  h_4(state, unused, out_2034104138300694595);
}
void pose_H_4(double *state, double *unused, double *out_7221129607300295927) {
  H_4(state, unused, out_7221129607300295927);
}
void pose_h_10(double *state, double *unused, double *out_1561728162162688074) {
  h_10(state, unused, out_1561728162162688074);
}
void pose_H_10(double *state, double *unused, double *out_8343161513752116907) {
  H_10(state, unused, out_8343161513752116907);
}
void pose_h_13(double *state, double *unused, double *out_425557749313340936) {
  h_13(state, unused, out_425557749313340936);
}
void pose_H_13(double *state, double *unused, double *out_389501601016405002) {
  H_13(state, unused, out_389501601016405002);
}
void pose_h_14(double *state, double *unused, double *out_6807261625183760659) {
  h_14(state, unused, out_6807261625183760659);
}
void pose_H_14(double *state, double *unused, double *out_3257888750960811398) {
  H_14(state, unused, out_3257888750960811398);
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
