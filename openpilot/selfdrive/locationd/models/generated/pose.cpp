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
void err_fun(double *nom_x, double *delta_x, double *out_3641871299484350556) {
   out_3641871299484350556[0] = delta_x[0] + nom_x[0];
   out_3641871299484350556[1] = delta_x[1] + nom_x[1];
   out_3641871299484350556[2] = delta_x[2] + nom_x[2];
   out_3641871299484350556[3] = delta_x[3] + nom_x[3];
   out_3641871299484350556[4] = delta_x[4] + nom_x[4];
   out_3641871299484350556[5] = delta_x[5] + nom_x[5];
   out_3641871299484350556[6] = delta_x[6] + nom_x[6];
   out_3641871299484350556[7] = delta_x[7] + nom_x[7];
   out_3641871299484350556[8] = delta_x[8] + nom_x[8];
   out_3641871299484350556[9] = delta_x[9] + nom_x[9];
   out_3641871299484350556[10] = delta_x[10] + nom_x[10];
   out_3641871299484350556[11] = delta_x[11] + nom_x[11];
   out_3641871299484350556[12] = delta_x[12] + nom_x[12];
   out_3641871299484350556[13] = delta_x[13] + nom_x[13];
   out_3641871299484350556[14] = delta_x[14] + nom_x[14];
   out_3641871299484350556[15] = delta_x[15] + nom_x[15];
   out_3641871299484350556[16] = delta_x[16] + nom_x[16];
   out_3641871299484350556[17] = delta_x[17] + nom_x[17];
}
void inv_err_fun(double *nom_x, double *true_x, double *out_3119284233878604394) {
   out_3119284233878604394[0] = -nom_x[0] + true_x[0];
   out_3119284233878604394[1] = -nom_x[1] + true_x[1];
   out_3119284233878604394[2] = -nom_x[2] + true_x[2];
   out_3119284233878604394[3] = -nom_x[3] + true_x[3];
   out_3119284233878604394[4] = -nom_x[4] + true_x[4];
   out_3119284233878604394[5] = -nom_x[5] + true_x[5];
   out_3119284233878604394[6] = -nom_x[6] + true_x[6];
   out_3119284233878604394[7] = -nom_x[7] + true_x[7];
   out_3119284233878604394[8] = -nom_x[8] + true_x[8];
   out_3119284233878604394[9] = -nom_x[9] + true_x[9];
   out_3119284233878604394[10] = -nom_x[10] + true_x[10];
   out_3119284233878604394[11] = -nom_x[11] + true_x[11];
   out_3119284233878604394[12] = -nom_x[12] + true_x[12];
   out_3119284233878604394[13] = -nom_x[13] + true_x[13];
   out_3119284233878604394[14] = -nom_x[14] + true_x[14];
   out_3119284233878604394[15] = -nom_x[15] + true_x[15];
   out_3119284233878604394[16] = -nom_x[16] + true_x[16];
   out_3119284233878604394[17] = -nom_x[17] + true_x[17];
}
void H_mod_fun(double *state, double *out_2783404226845349256) {
   out_2783404226845349256[0] = 1.0;
   out_2783404226845349256[1] = 0.0;
   out_2783404226845349256[2] = 0.0;
   out_2783404226845349256[3] = 0.0;
   out_2783404226845349256[4] = 0.0;
   out_2783404226845349256[5] = 0.0;
   out_2783404226845349256[6] = 0.0;
   out_2783404226845349256[7] = 0.0;
   out_2783404226845349256[8] = 0.0;
   out_2783404226845349256[9] = 0.0;
   out_2783404226845349256[10] = 0.0;
   out_2783404226845349256[11] = 0.0;
   out_2783404226845349256[12] = 0.0;
   out_2783404226845349256[13] = 0.0;
   out_2783404226845349256[14] = 0.0;
   out_2783404226845349256[15] = 0.0;
   out_2783404226845349256[16] = 0.0;
   out_2783404226845349256[17] = 0.0;
   out_2783404226845349256[18] = 0.0;
   out_2783404226845349256[19] = 1.0;
   out_2783404226845349256[20] = 0.0;
   out_2783404226845349256[21] = 0.0;
   out_2783404226845349256[22] = 0.0;
   out_2783404226845349256[23] = 0.0;
   out_2783404226845349256[24] = 0.0;
   out_2783404226845349256[25] = 0.0;
   out_2783404226845349256[26] = 0.0;
   out_2783404226845349256[27] = 0.0;
   out_2783404226845349256[28] = 0.0;
   out_2783404226845349256[29] = 0.0;
   out_2783404226845349256[30] = 0.0;
   out_2783404226845349256[31] = 0.0;
   out_2783404226845349256[32] = 0.0;
   out_2783404226845349256[33] = 0.0;
   out_2783404226845349256[34] = 0.0;
   out_2783404226845349256[35] = 0.0;
   out_2783404226845349256[36] = 0.0;
   out_2783404226845349256[37] = 0.0;
   out_2783404226845349256[38] = 1.0;
   out_2783404226845349256[39] = 0.0;
   out_2783404226845349256[40] = 0.0;
   out_2783404226845349256[41] = 0.0;
   out_2783404226845349256[42] = 0.0;
   out_2783404226845349256[43] = 0.0;
   out_2783404226845349256[44] = 0.0;
   out_2783404226845349256[45] = 0.0;
   out_2783404226845349256[46] = 0.0;
   out_2783404226845349256[47] = 0.0;
   out_2783404226845349256[48] = 0.0;
   out_2783404226845349256[49] = 0.0;
   out_2783404226845349256[50] = 0.0;
   out_2783404226845349256[51] = 0.0;
   out_2783404226845349256[52] = 0.0;
   out_2783404226845349256[53] = 0.0;
   out_2783404226845349256[54] = 0.0;
   out_2783404226845349256[55] = 0.0;
   out_2783404226845349256[56] = 0.0;
   out_2783404226845349256[57] = 1.0;
   out_2783404226845349256[58] = 0.0;
   out_2783404226845349256[59] = 0.0;
   out_2783404226845349256[60] = 0.0;
   out_2783404226845349256[61] = 0.0;
   out_2783404226845349256[62] = 0.0;
   out_2783404226845349256[63] = 0.0;
   out_2783404226845349256[64] = 0.0;
   out_2783404226845349256[65] = 0.0;
   out_2783404226845349256[66] = 0.0;
   out_2783404226845349256[67] = 0.0;
   out_2783404226845349256[68] = 0.0;
   out_2783404226845349256[69] = 0.0;
   out_2783404226845349256[70] = 0.0;
   out_2783404226845349256[71] = 0.0;
   out_2783404226845349256[72] = 0.0;
   out_2783404226845349256[73] = 0.0;
   out_2783404226845349256[74] = 0.0;
   out_2783404226845349256[75] = 0.0;
   out_2783404226845349256[76] = 1.0;
   out_2783404226845349256[77] = 0.0;
   out_2783404226845349256[78] = 0.0;
   out_2783404226845349256[79] = 0.0;
   out_2783404226845349256[80] = 0.0;
   out_2783404226845349256[81] = 0.0;
   out_2783404226845349256[82] = 0.0;
   out_2783404226845349256[83] = 0.0;
   out_2783404226845349256[84] = 0.0;
   out_2783404226845349256[85] = 0.0;
   out_2783404226845349256[86] = 0.0;
   out_2783404226845349256[87] = 0.0;
   out_2783404226845349256[88] = 0.0;
   out_2783404226845349256[89] = 0.0;
   out_2783404226845349256[90] = 0.0;
   out_2783404226845349256[91] = 0.0;
   out_2783404226845349256[92] = 0.0;
   out_2783404226845349256[93] = 0.0;
   out_2783404226845349256[94] = 0.0;
   out_2783404226845349256[95] = 1.0;
   out_2783404226845349256[96] = 0.0;
   out_2783404226845349256[97] = 0.0;
   out_2783404226845349256[98] = 0.0;
   out_2783404226845349256[99] = 0.0;
   out_2783404226845349256[100] = 0.0;
   out_2783404226845349256[101] = 0.0;
   out_2783404226845349256[102] = 0.0;
   out_2783404226845349256[103] = 0.0;
   out_2783404226845349256[104] = 0.0;
   out_2783404226845349256[105] = 0.0;
   out_2783404226845349256[106] = 0.0;
   out_2783404226845349256[107] = 0.0;
   out_2783404226845349256[108] = 0.0;
   out_2783404226845349256[109] = 0.0;
   out_2783404226845349256[110] = 0.0;
   out_2783404226845349256[111] = 0.0;
   out_2783404226845349256[112] = 0.0;
   out_2783404226845349256[113] = 0.0;
   out_2783404226845349256[114] = 1.0;
   out_2783404226845349256[115] = 0.0;
   out_2783404226845349256[116] = 0.0;
   out_2783404226845349256[117] = 0.0;
   out_2783404226845349256[118] = 0.0;
   out_2783404226845349256[119] = 0.0;
   out_2783404226845349256[120] = 0.0;
   out_2783404226845349256[121] = 0.0;
   out_2783404226845349256[122] = 0.0;
   out_2783404226845349256[123] = 0.0;
   out_2783404226845349256[124] = 0.0;
   out_2783404226845349256[125] = 0.0;
   out_2783404226845349256[126] = 0.0;
   out_2783404226845349256[127] = 0.0;
   out_2783404226845349256[128] = 0.0;
   out_2783404226845349256[129] = 0.0;
   out_2783404226845349256[130] = 0.0;
   out_2783404226845349256[131] = 0.0;
   out_2783404226845349256[132] = 0.0;
   out_2783404226845349256[133] = 1.0;
   out_2783404226845349256[134] = 0.0;
   out_2783404226845349256[135] = 0.0;
   out_2783404226845349256[136] = 0.0;
   out_2783404226845349256[137] = 0.0;
   out_2783404226845349256[138] = 0.0;
   out_2783404226845349256[139] = 0.0;
   out_2783404226845349256[140] = 0.0;
   out_2783404226845349256[141] = 0.0;
   out_2783404226845349256[142] = 0.0;
   out_2783404226845349256[143] = 0.0;
   out_2783404226845349256[144] = 0.0;
   out_2783404226845349256[145] = 0.0;
   out_2783404226845349256[146] = 0.0;
   out_2783404226845349256[147] = 0.0;
   out_2783404226845349256[148] = 0.0;
   out_2783404226845349256[149] = 0.0;
   out_2783404226845349256[150] = 0.0;
   out_2783404226845349256[151] = 0.0;
   out_2783404226845349256[152] = 1.0;
   out_2783404226845349256[153] = 0.0;
   out_2783404226845349256[154] = 0.0;
   out_2783404226845349256[155] = 0.0;
   out_2783404226845349256[156] = 0.0;
   out_2783404226845349256[157] = 0.0;
   out_2783404226845349256[158] = 0.0;
   out_2783404226845349256[159] = 0.0;
   out_2783404226845349256[160] = 0.0;
   out_2783404226845349256[161] = 0.0;
   out_2783404226845349256[162] = 0.0;
   out_2783404226845349256[163] = 0.0;
   out_2783404226845349256[164] = 0.0;
   out_2783404226845349256[165] = 0.0;
   out_2783404226845349256[166] = 0.0;
   out_2783404226845349256[167] = 0.0;
   out_2783404226845349256[168] = 0.0;
   out_2783404226845349256[169] = 0.0;
   out_2783404226845349256[170] = 0.0;
   out_2783404226845349256[171] = 1.0;
   out_2783404226845349256[172] = 0.0;
   out_2783404226845349256[173] = 0.0;
   out_2783404226845349256[174] = 0.0;
   out_2783404226845349256[175] = 0.0;
   out_2783404226845349256[176] = 0.0;
   out_2783404226845349256[177] = 0.0;
   out_2783404226845349256[178] = 0.0;
   out_2783404226845349256[179] = 0.0;
   out_2783404226845349256[180] = 0.0;
   out_2783404226845349256[181] = 0.0;
   out_2783404226845349256[182] = 0.0;
   out_2783404226845349256[183] = 0.0;
   out_2783404226845349256[184] = 0.0;
   out_2783404226845349256[185] = 0.0;
   out_2783404226845349256[186] = 0.0;
   out_2783404226845349256[187] = 0.0;
   out_2783404226845349256[188] = 0.0;
   out_2783404226845349256[189] = 0.0;
   out_2783404226845349256[190] = 1.0;
   out_2783404226845349256[191] = 0.0;
   out_2783404226845349256[192] = 0.0;
   out_2783404226845349256[193] = 0.0;
   out_2783404226845349256[194] = 0.0;
   out_2783404226845349256[195] = 0.0;
   out_2783404226845349256[196] = 0.0;
   out_2783404226845349256[197] = 0.0;
   out_2783404226845349256[198] = 0.0;
   out_2783404226845349256[199] = 0.0;
   out_2783404226845349256[200] = 0.0;
   out_2783404226845349256[201] = 0.0;
   out_2783404226845349256[202] = 0.0;
   out_2783404226845349256[203] = 0.0;
   out_2783404226845349256[204] = 0.0;
   out_2783404226845349256[205] = 0.0;
   out_2783404226845349256[206] = 0.0;
   out_2783404226845349256[207] = 0.0;
   out_2783404226845349256[208] = 0.0;
   out_2783404226845349256[209] = 1.0;
   out_2783404226845349256[210] = 0.0;
   out_2783404226845349256[211] = 0.0;
   out_2783404226845349256[212] = 0.0;
   out_2783404226845349256[213] = 0.0;
   out_2783404226845349256[214] = 0.0;
   out_2783404226845349256[215] = 0.0;
   out_2783404226845349256[216] = 0.0;
   out_2783404226845349256[217] = 0.0;
   out_2783404226845349256[218] = 0.0;
   out_2783404226845349256[219] = 0.0;
   out_2783404226845349256[220] = 0.0;
   out_2783404226845349256[221] = 0.0;
   out_2783404226845349256[222] = 0.0;
   out_2783404226845349256[223] = 0.0;
   out_2783404226845349256[224] = 0.0;
   out_2783404226845349256[225] = 0.0;
   out_2783404226845349256[226] = 0.0;
   out_2783404226845349256[227] = 0.0;
   out_2783404226845349256[228] = 1.0;
   out_2783404226845349256[229] = 0.0;
   out_2783404226845349256[230] = 0.0;
   out_2783404226845349256[231] = 0.0;
   out_2783404226845349256[232] = 0.0;
   out_2783404226845349256[233] = 0.0;
   out_2783404226845349256[234] = 0.0;
   out_2783404226845349256[235] = 0.0;
   out_2783404226845349256[236] = 0.0;
   out_2783404226845349256[237] = 0.0;
   out_2783404226845349256[238] = 0.0;
   out_2783404226845349256[239] = 0.0;
   out_2783404226845349256[240] = 0.0;
   out_2783404226845349256[241] = 0.0;
   out_2783404226845349256[242] = 0.0;
   out_2783404226845349256[243] = 0.0;
   out_2783404226845349256[244] = 0.0;
   out_2783404226845349256[245] = 0.0;
   out_2783404226845349256[246] = 0.0;
   out_2783404226845349256[247] = 1.0;
   out_2783404226845349256[248] = 0.0;
   out_2783404226845349256[249] = 0.0;
   out_2783404226845349256[250] = 0.0;
   out_2783404226845349256[251] = 0.0;
   out_2783404226845349256[252] = 0.0;
   out_2783404226845349256[253] = 0.0;
   out_2783404226845349256[254] = 0.0;
   out_2783404226845349256[255] = 0.0;
   out_2783404226845349256[256] = 0.0;
   out_2783404226845349256[257] = 0.0;
   out_2783404226845349256[258] = 0.0;
   out_2783404226845349256[259] = 0.0;
   out_2783404226845349256[260] = 0.0;
   out_2783404226845349256[261] = 0.0;
   out_2783404226845349256[262] = 0.0;
   out_2783404226845349256[263] = 0.0;
   out_2783404226845349256[264] = 0.0;
   out_2783404226845349256[265] = 0.0;
   out_2783404226845349256[266] = 1.0;
   out_2783404226845349256[267] = 0.0;
   out_2783404226845349256[268] = 0.0;
   out_2783404226845349256[269] = 0.0;
   out_2783404226845349256[270] = 0.0;
   out_2783404226845349256[271] = 0.0;
   out_2783404226845349256[272] = 0.0;
   out_2783404226845349256[273] = 0.0;
   out_2783404226845349256[274] = 0.0;
   out_2783404226845349256[275] = 0.0;
   out_2783404226845349256[276] = 0.0;
   out_2783404226845349256[277] = 0.0;
   out_2783404226845349256[278] = 0.0;
   out_2783404226845349256[279] = 0.0;
   out_2783404226845349256[280] = 0.0;
   out_2783404226845349256[281] = 0.0;
   out_2783404226845349256[282] = 0.0;
   out_2783404226845349256[283] = 0.0;
   out_2783404226845349256[284] = 0.0;
   out_2783404226845349256[285] = 1.0;
   out_2783404226845349256[286] = 0.0;
   out_2783404226845349256[287] = 0.0;
   out_2783404226845349256[288] = 0.0;
   out_2783404226845349256[289] = 0.0;
   out_2783404226845349256[290] = 0.0;
   out_2783404226845349256[291] = 0.0;
   out_2783404226845349256[292] = 0.0;
   out_2783404226845349256[293] = 0.0;
   out_2783404226845349256[294] = 0.0;
   out_2783404226845349256[295] = 0.0;
   out_2783404226845349256[296] = 0.0;
   out_2783404226845349256[297] = 0.0;
   out_2783404226845349256[298] = 0.0;
   out_2783404226845349256[299] = 0.0;
   out_2783404226845349256[300] = 0.0;
   out_2783404226845349256[301] = 0.0;
   out_2783404226845349256[302] = 0.0;
   out_2783404226845349256[303] = 0.0;
   out_2783404226845349256[304] = 1.0;
   out_2783404226845349256[305] = 0.0;
   out_2783404226845349256[306] = 0.0;
   out_2783404226845349256[307] = 0.0;
   out_2783404226845349256[308] = 0.0;
   out_2783404226845349256[309] = 0.0;
   out_2783404226845349256[310] = 0.0;
   out_2783404226845349256[311] = 0.0;
   out_2783404226845349256[312] = 0.0;
   out_2783404226845349256[313] = 0.0;
   out_2783404226845349256[314] = 0.0;
   out_2783404226845349256[315] = 0.0;
   out_2783404226845349256[316] = 0.0;
   out_2783404226845349256[317] = 0.0;
   out_2783404226845349256[318] = 0.0;
   out_2783404226845349256[319] = 0.0;
   out_2783404226845349256[320] = 0.0;
   out_2783404226845349256[321] = 0.0;
   out_2783404226845349256[322] = 0.0;
   out_2783404226845349256[323] = 1.0;
}
void f_fun(double *state, double dt, double *out_5949144455846088993) {
   out_5949144455846088993[0] = atan2((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), -(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]));
   out_5949144455846088993[1] = asin(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]));
   out_5949144455846088993[2] = atan2(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), -(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]));
   out_5949144455846088993[3] = dt*state[12] + state[3];
   out_5949144455846088993[4] = dt*state[13] + state[4];
   out_5949144455846088993[5] = dt*state[14] + state[5];
   out_5949144455846088993[6] = state[6];
   out_5949144455846088993[7] = state[7];
   out_5949144455846088993[8] = state[8];
   out_5949144455846088993[9] = state[9];
   out_5949144455846088993[10] = state[10];
   out_5949144455846088993[11] = state[11];
   out_5949144455846088993[12] = state[12];
   out_5949144455846088993[13] = state[13];
   out_5949144455846088993[14] = state[14];
   out_5949144455846088993[15] = state[15];
   out_5949144455846088993[16] = state[16];
   out_5949144455846088993[17] = state[17];
}
void F_fun(double *state, double dt, double *out_7424333812317239085) {
   out_7424333812317239085[0] = ((-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*cos(state[0])*cos(state[1]) - sin(state[0])*cos(dt*state[6])*cos(dt*state[7])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + ((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*cos(state[0])*cos(state[1]) - sin(dt*state[6])*sin(state[0])*cos(dt*state[7])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_7424333812317239085[1] = ((-sin(dt*state[6])*sin(dt*state[8]) - sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*cos(state[1]) - (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*sin(state[1]) - sin(state[1])*cos(dt*state[6])*cos(dt*state[7])*cos(state[0]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*sin(state[1]) + (-sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) + sin(dt*state[8])*cos(dt*state[6]))*cos(state[1]) - sin(dt*state[6])*sin(state[1])*cos(dt*state[7])*cos(state[0]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_7424333812317239085[2] = 0;
   out_7424333812317239085[3] = 0;
   out_7424333812317239085[4] = 0;
   out_7424333812317239085[5] = 0;
   out_7424333812317239085[6] = (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(dt*cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*sin(dt*state[8]) - dt*sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-dt*sin(dt*state[6])*cos(dt*state[8]) + dt*sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) - dt*cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (dt*sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_7424333812317239085[7] = (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[6])*sin(dt*state[7])*cos(state[0])*cos(state[1]) + dt*sin(dt*state[6])*sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) - dt*sin(dt*state[6])*sin(state[1])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[7])*cos(dt*state[6])*cos(state[0])*cos(state[1]) + dt*sin(dt*state[8])*sin(state[0])*cos(dt*state[6])*cos(dt*state[7])*cos(state[1]) - dt*sin(state[1])*cos(dt*state[6])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_7424333812317239085[8] = ((dt*sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + dt*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (dt*sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + ((dt*sin(dt*state[6])*sin(dt*state[8]) + dt*sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*cos(dt*state[8]) + dt*sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_7424333812317239085[9] = 0;
   out_7424333812317239085[10] = 0;
   out_7424333812317239085[11] = 0;
   out_7424333812317239085[12] = 0;
   out_7424333812317239085[13] = 0;
   out_7424333812317239085[14] = 0;
   out_7424333812317239085[15] = 0;
   out_7424333812317239085[16] = 0;
   out_7424333812317239085[17] = 0;
   out_7424333812317239085[18] = (-sin(dt*state[7])*sin(state[0])*cos(state[1]) - sin(dt*state[8])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_7424333812317239085[19] = (-sin(dt*state[7])*sin(state[1])*cos(state[0]) + sin(dt*state[8])*sin(state[0])*sin(state[1])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_7424333812317239085[20] = 0;
   out_7424333812317239085[21] = 0;
   out_7424333812317239085[22] = 0;
   out_7424333812317239085[23] = 0;
   out_7424333812317239085[24] = 0;
   out_7424333812317239085[25] = (dt*sin(dt*state[7])*sin(dt*state[8])*sin(state[0])*cos(state[1]) - dt*sin(dt*state[7])*sin(state[1])*cos(dt*state[8]) + dt*cos(dt*state[7])*cos(state[0])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_7424333812317239085[26] = (-dt*sin(dt*state[8])*sin(state[1])*cos(dt*state[7]) - dt*sin(state[0])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_7424333812317239085[27] = 0;
   out_7424333812317239085[28] = 0;
   out_7424333812317239085[29] = 0;
   out_7424333812317239085[30] = 0;
   out_7424333812317239085[31] = 0;
   out_7424333812317239085[32] = 0;
   out_7424333812317239085[33] = 0;
   out_7424333812317239085[34] = 0;
   out_7424333812317239085[35] = 0;
   out_7424333812317239085[36] = ((sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[7]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[7]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_7424333812317239085[37] = (-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(-sin(dt*state[7])*sin(state[2])*cos(state[0])*cos(state[1]) + sin(dt*state[8])*sin(state[0])*sin(state[2])*cos(dt*state[7])*cos(state[1]) - sin(state[1])*sin(state[2])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*(-sin(dt*state[7])*cos(state[0])*cos(state[1])*cos(state[2]) + sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1])*cos(state[2]) - sin(state[1])*cos(dt*state[7])*cos(dt*state[8])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_7424333812317239085[38] = ((-sin(state[0])*sin(state[2]) - sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (-sin(state[0])*sin(state[1])*sin(state[2]) - cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_7424333812317239085[39] = 0;
   out_7424333812317239085[40] = 0;
   out_7424333812317239085[41] = 0;
   out_7424333812317239085[42] = 0;
   out_7424333812317239085[43] = (-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(dt*(sin(state[0])*cos(state[2]) - sin(state[1])*sin(state[2])*cos(state[0]))*cos(dt*state[7]) - dt*(sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[7])*sin(dt*state[8]) - dt*sin(dt*state[7])*sin(state[2])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*(dt*(-sin(state[0])*sin(state[2]) - sin(state[1])*cos(state[0])*cos(state[2]))*cos(dt*state[7]) - dt*(sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[7])*sin(dt*state[8]) - dt*sin(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_7424333812317239085[44] = (dt*(sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*cos(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*sin(state[2])*cos(dt*state[7])*cos(state[1]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + (dt*(sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*cos(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[7])*cos(state[1])*cos(state[2]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_7424333812317239085[45] = 0;
   out_7424333812317239085[46] = 0;
   out_7424333812317239085[47] = 0;
   out_7424333812317239085[48] = 0;
   out_7424333812317239085[49] = 0;
   out_7424333812317239085[50] = 0;
   out_7424333812317239085[51] = 0;
   out_7424333812317239085[52] = 0;
   out_7424333812317239085[53] = 0;
   out_7424333812317239085[54] = 0;
   out_7424333812317239085[55] = 0;
   out_7424333812317239085[56] = 0;
   out_7424333812317239085[57] = 1;
   out_7424333812317239085[58] = 0;
   out_7424333812317239085[59] = 0;
   out_7424333812317239085[60] = 0;
   out_7424333812317239085[61] = 0;
   out_7424333812317239085[62] = 0;
   out_7424333812317239085[63] = 0;
   out_7424333812317239085[64] = 0;
   out_7424333812317239085[65] = 0;
   out_7424333812317239085[66] = dt;
   out_7424333812317239085[67] = 0;
   out_7424333812317239085[68] = 0;
   out_7424333812317239085[69] = 0;
   out_7424333812317239085[70] = 0;
   out_7424333812317239085[71] = 0;
   out_7424333812317239085[72] = 0;
   out_7424333812317239085[73] = 0;
   out_7424333812317239085[74] = 0;
   out_7424333812317239085[75] = 0;
   out_7424333812317239085[76] = 1;
   out_7424333812317239085[77] = 0;
   out_7424333812317239085[78] = 0;
   out_7424333812317239085[79] = 0;
   out_7424333812317239085[80] = 0;
   out_7424333812317239085[81] = 0;
   out_7424333812317239085[82] = 0;
   out_7424333812317239085[83] = 0;
   out_7424333812317239085[84] = 0;
   out_7424333812317239085[85] = dt;
   out_7424333812317239085[86] = 0;
   out_7424333812317239085[87] = 0;
   out_7424333812317239085[88] = 0;
   out_7424333812317239085[89] = 0;
   out_7424333812317239085[90] = 0;
   out_7424333812317239085[91] = 0;
   out_7424333812317239085[92] = 0;
   out_7424333812317239085[93] = 0;
   out_7424333812317239085[94] = 0;
   out_7424333812317239085[95] = 1;
   out_7424333812317239085[96] = 0;
   out_7424333812317239085[97] = 0;
   out_7424333812317239085[98] = 0;
   out_7424333812317239085[99] = 0;
   out_7424333812317239085[100] = 0;
   out_7424333812317239085[101] = 0;
   out_7424333812317239085[102] = 0;
   out_7424333812317239085[103] = 0;
   out_7424333812317239085[104] = dt;
   out_7424333812317239085[105] = 0;
   out_7424333812317239085[106] = 0;
   out_7424333812317239085[107] = 0;
   out_7424333812317239085[108] = 0;
   out_7424333812317239085[109] = 0;
   out_7424333812317239085[110] = 0;
   out_7424333812317239085[111] = 0;
   out_7424333812317239085[112] = 0;
   out_7424333812317239085[113] = 0;
   out_7424333812317239085[114] = 1;
   out_7424333812317239085[115] = 0;
   out_7424333812317239085[116] = 0;
   out_7424333812317239085[117] = 0;
   out_7424333812317239085[118] = 0;
   out_7424333812317239085[119] = 0;
   out_7424333812317239085[120] = 0;
   out_7424333812317239085[121] = 0;
   out_7424333812317239085[122] = 0;
   out_7424333812317239085[123] = 0;
   out_7424333812317239085[124] = 0;
   out_7424333812317239085[125] = 0;
   out_7424333812317239085[126] = 0;
   out_7424333812317239085[127] = 0;
   out_7424333812317239085[128] = 0;
   out_7424333812317239085[129] = 0;
   out_7424333812317239085[130] = 0;
   out_7424333812317239085[131] = 0;
   out_7424333812317239085[132] = 0;
   out_7424333812317239085[133] = 1;
   out_7424333812317239085[134] = 0;
   out_7424333812317239085[135] = 0;
   out_7424333812317239085[136] = 0;
   out_7424333812317239085[137] = 0;
   out_7424333812317239085[138] = 0;
   out_7424333812317239085[139] = 0;
   out_7424333812317239085[140] = 0;
   out_7424333812317239085[141] = 0;
   out_7424333812317239085[142] = 0;
   out_7424333812317239085[143] = 0;
   out_7424333812317239085[144] = 0;
   out_7424333812317239085[145] = 0;
   out_7424333812317239085[146] = 0;
   out_7424333812317239085[147] = 0;
   out_7424333812317239085[148] = 0;
   out_7424333812317239085[149] = 0;
   out_7424333812317239085[150] = 0;
   out_7424333812317239085[151] = 0;
   out_7424333812317239085[152] = 1;
   out_7424333812317239085[153] = 0;
   out_7424333812317239085[154] = 0;
   out_7424333812317239085[155] = 0;
   out_7424333812317239085[156] = 0;
   out_7424333812317239085[157] = 0;
   out_7424333812317239085[158] = 0;
   out_7424333812317239085[159] = 0;
   out_7424333812317239085[160] = 0;
   out_7424333812317239085[161] = 0;
   out_7424333812317239085[162] = 0;
   out_7424333812317239085[163] = 0;
   out_7424333812317239085[164] = 0;
   out_7424333812317239085[165] = 0;
   out_7424333812317239085[166] = 0;
   out_7424333812317239085[167] = 0;
   out_7424333812317239085[168] = 0;
   out_7424333812317239085[169] = 0;
   out_7424333812317239085[170] = 0;
   out_7424333812317239085[171] = 1;
   out_7424333812317239085[172] = 0;
   out_7424333812317239085[173] = 0;
   out_7424333812317239085[174] = 0;
   out_7424333812317239085[175] = 0;
   out_7424333812317239085[176] = 0;
   out_7424333812317239085[177] = 0;
   out_7424333812317239085[178] = 0;
   out_7424333812317239085[179] = 0;
   out_7424333812317239085[180] = 0;
   out_7424333812317239085[181] = 0;
   out_7424333812317239085[182] = 0;
   out_7424333812317239085[183] = 0;
   out_7424333812317239085[184] = 0;
   out_7424333812317239085[185] = 0;
   out_7424333812317239085[186] = 0;
   out_7424333812317239085[187] = 0;
   out_7424333812317239085[188] = 0;
   out_7424333812317239085[189] = 0;
   out_7424333812317239085[190] = 1;
   out_7424333812317239085[191] = 0;
   out_7424333812317239085[192] = 0;
   out_7424333812317239085[193] = 0;
   out_7424333812317239085[194] = 0;
   out_7424333812317239085[195] = 0;
   out_7424333812317239085[196] = 0;
   out_7424333812317239085[197] = 0;
   out_7424333812317239085[198] = 0;
   out_7424333812317239085[199] = 0;
   out_7424333812317239085[200] = 0;
   out_7424333812317239085[201] = 0;
   out_7424333812317239085[202] = 0;
   out_7424333812317239085[203] = 0;
   out_7424333812317239085[204] = 0;
   out_7424333812317239085[205] = 0;
   out_7424333812317239085[206] = 0;
   out_7424333812317239085[207] = 0;
   out_7424333812317239085[208] = 0;
   out_7424333812317239085[209] = 1;
   out_7424333812317239085[210] = 0;
   out_7424333812317239085[211] = 0;
   out_7424333812317239085[212] = 0;
   out_7424333812317239085[213] = 0;
   out_7424333812317239085[214] = 0;
   out_7424333812317239085[215] = 0;
   out_7424333812317239085[216] = 0;
   out_7424333812317239085[217] = 0;
   out_7424333812317239085[218] = 0;
   out_7424333812317239085[219] = 0;
   out_7424333812317239085[220] = 0;
   out_7424333812317239085[221] = 0;
   out_7424333812317239085[222] = 0;
   out_7424333812317239085[223] = 0;
   out_7424333812317239085[224] = 0;
   out_7424333812317239085[225] = 0;
   out_7424333812317239085[226] = 0;
   out_7424333812317239085[227] = 0;
   out_7424333812317239085[228] = 1;
   out_7424333812317239085[229] = 0;
   out_7424333812317239085[230] = 0;
   out_7424333812317239085[231] = 0;
   out_7424333812317239085[232] = 0;
   out_7424333812317239085[233] = 0;
   out_7424333812317239085[234] = 0;
   out_7424333812317239085[235] = 0;
   out_7424333812317239085[236] = 0;
   out_7424333812317239085[237] = 0;
   out_7424333812317239085[238] = 0;
   out_7424333812317239085[239] = 0;
   out_7424333812317239085[240] = 0;
   out_7424333812317239085[241] = 0;
   out_7424333812317239085[242] = 0;
   out_7424333812317239085[243] = 0;
   out_7424333812317239085[244] = 0;
   out_7424333812317239085[245] = 0;
   out_7424333812317239085[246] = 0;
   out_7424333812317239085[247] = 1;
   out_7424333812317239085[248] = 0;
   out_7424333812317239085[249] = 0;
   out_7424333812317239085[250] = 0;
   out_7424333812317239085[251] = 0;
   out_7424333812317239085[252] = 0;
   out_7424333812317239085[253] = 0;
   out_7424333812317239085[254] = 0;
   out_7424333812317239085[255] = 0;
   out_7424333812317239085[256] = 0;
   out_7424333812317239085[257] = 0;
   out_7424333812317239085[258] = 0;
   out_7424333812317239085[259] = 0;
   out_7424333812317239085[260] = 0;
   out_7424333812317239085[261] = 0;
   out_7424333812317239085[262] = 0;
   out_7424333812317239085[263] = 0;
   out_7424333812317239085[264] = 0;
   out_7424333812317239085[265] = 0;
   out_7424333812317239085[266] = 1;
   out_7424333812317239085[267] = 0;
   out_7424333812317239085[268] = 0;
   out_7424333812317239085[269] = 0;
   out_7424333812317239085[270] = 0;
   out_7424333812317239085[271] = 0;
   out_7424333812317239085[272] = 0;
   out_7424333812317239085[273] = 0;
   out_7424333812317239085[274] = 0;
   out_7424333812317239085[275] = 0;
   out_7424333812317239085[276] = 0;
   out_7424333812317239085[277] = 0;
   out_7424333812317239085[278] = 0;
   out_7424333812317239085[279] = 0;
   out_7424333812317239085[280] = 0;
   out_7424333812317239085[281] = 0;
   out_7424333812317239085[282] = 0;
   out_7424333812317239085[283] = 0;
   out_7424333812317239085[284] = 0;
   out_7424333812317239085[285] = 1;
   out_7424333812317239085[286] = 0;
   out_7424333812317239085[287] = 0;
   out_7424333812317239085[288] = 0;
   out_7424333812317239085[289] = 0;
   out_7424333812317239085[290] = 0;
   out_7424333812317239085[291] = 0;
   out_7424333812317239085[292] = 0;
   out_7424333812317239085[293] = 0;
   out_7424333812317239085[294] = 0;
   out_7424333812317239085[295] = 0;
   out_7424333812317239085[296] = 0;
   out_7424333812317239085[297] = 0;
   out_7424333812317239085[298] = 0;
   out_7424333812317239085[299] = 0;
   out_7424333812317239085[300] = 0;
   out_7424333812317239085[301] = 0;
   out_7424333812317239085[302] = 0;
   out_7424333812317239085[303] = 0;
   out_7424333812317239085[304] = 1;
   out_7424333812317239085[305] = 0;
   out_7424333812317239085[306] = 0;
   out_7424333812317239085[307] = 0;
   out_7424333812317239085[308] = 0;
   out_7424333812317239085[309] = 0;
   out_7424333812317239085[310] = 0;
   out_7424333812317239085[311] = 0;
   out_7424333812317239085[312] = 0;
   out_7424333812317239085[313] = 0;
   out_7424333812317239085[314] = 0;
   out_7424333812317239085[315] = 0;
   out_7424333812317239085[316] = 0;
   out_7424333812317239085[317] = 0;
   out_7424333812317239085[318] = 0;
   out_7424333812317239085[319] = 0;
   out_7424333812317239085[320] = 0;
   out_7424333812317239085[321] = 0;
   out_7424333812317239085[322] = 0;
   out_7424333812317239085[323] = 1;
}
void h_4(double *state, double *unused, double *out_8321002018191485436) {
   out_8321002018191485436[0] = state[6] + state[9];
   out_8321002018191485436[1] = state[7] + state[10];
   out_8321002018191485436[2] = state[8] + state[11];
}
void H_4(double *state, double *unused, double *out_5362062883923420523) {
   out_5362062883923420523[0] = 0;
   out_5362062883923420523[1] = 0;
   out_5362062883923420523[2] = 0;
   out_5362062883923420523[3] = 0;
   out_5362062883923420523[4] = 0;
   out_5362062883923420523[5] = 0;
   out_5362062883923420523[6] = 1;
   out_5362062883923420523[7] = 0;
   out_5362062883923420523[8] = 0;
   out_5362062883923420523[9] = 1;
   out_5362062883923420523[10] = 0;
   out_5362062883923420523[11] = 0;
   out_5362062883923420523[12] = 0;
   out_5362062883923420523[13] = 0;
   out_5362062883923420523[14] = 0;
   out_5362062883923420523[15] = 0;
   out_5362062883923420523[16] = 0;
   out_5362062883923420523[17] = 0;
   out_5362062883923420523[18] = 0;
   out_5362062883923420523[19] = 0;
   out_5362062883923420523[20] = 0;
   out_5362062883923420523[21] = 0;
   out_5362062883923420523[22] = 0;
   out_5362062883923420523[23] = 0;
   out_5362062883923420523[24] = 0;
   out_5362062883923420523[25] = 1;
   out_5362062883923420523[26] = 0;
   out_5362062883923420523[27] = 0;
   out_5362062883923420523[28] = 1;
   out_5362062883923420523[29] = 0;
   out_5362062883923420523[30] = 0;
   out_5362062883923420523[31] = 0;
   out_5362062883923420523[32] = 0;
   out_5362062883923420523[33] = 0;
   out_5362062883923420523[34] = 0;
   out_5362062883923420523[35] = 0;
   out_5362062883923420523[36] = 0;
   out_5362062883923420523[37] = 0;
   out_5362062883923420523[38] = 0;
   out_5362062883923420523[39] = 0;
   out_5362062883923420523[40] = 0;
   out_5362062883923420523[41] = 0;
   out_5362062883923420523[42] = 0;
   out_5362062883923420523[43] = 0;
   out_5362062883923420523[44] = 1;
   out_5362062883923420523[45] = 0;
   out_5362062883923420523[46] = 0;
   out_5362062883923420523[47] = 1;
   out_5362062883923420523[48] = 0;
   out_5362062883923420523[49] = 0;
   out_5362062883923420523[50] = 0;
   out_5362062883923420523[51] = 0;
   out_5362062883923420523[52] = 0;
   out_5362062883923420523[53] = 0;
}
void h_10(double *state, double *unused, double *out_2988408482111357830) {
   out_2988408482111357830[0] = 9.8100000000000005*sin(state[1]) - state[4]*state[8] + state[5]*state[7] + state[12] + state[15];
   out_2988408482111357830[1] = -9.8100000000000005*sin(state[0])*cos(state[1]) + state[3]*state[8] - state[5]*state[6] + state[13] + state[16];
   out_2988408482111357830[2] = -9.8100000000000005*cos(state[0])*cos(state[1]) - state[3]*state[7] + state[4]*state[6] + state[14] + state[17];
}
void H_10(double *state, double *unused, double *out_298758434706635924) {
   out_298758434706635924[0] = 0;
   out_298758434706635924[1] = 9.8100000000000005*cos(state[1]);
   out_298758434706635924[2] = 0;
   out_298758434706635924[3] = 0;
   out_298758434706635924[4] = -state[8];
   out_298758434706635924[5] = state[7];
   out_298758434706635924[6] = 0;
   out_298758434706635924[7] = state[5];
   out_298758434706635924[8] = -state[4];
   out_298758434706635924[9] = 0;
   out_298758434706635924[10] = 0;
   out_298758434706635924[11] = 0;
   out_298758434706635924[12] = 1;
   out_298758434706635924[13] = 0;
   out_298758434706635924[14] = 0;
   out_298758434706635924[15] = 1;
   out_298758434706635924[16] = 0;
   out_298758434706635924[17] = 0;
   out_298758434706635924[18] = -9.8100000000000005*cos(state[0])*cos(state[1]);
   out_298758434706635924[19] = 9.8100000000000005*sin(state[0])*sin(state[1]);
   out_298758434706635924[20] = 0;
   out_298758434706635924[21] = state[8];
   out_298758434706635924[22] = 0;
   out_298758434706635924[23] = -state[6];
   out_298758434706635924[24] = -state[5];
   out_298758434706635924[25] = 0;
   out_298758434706635924[26] = state[3];
   out_298758434706635924[27] = 0;
   out_298758434706635924[28] = 0;
   out_298758434706635924[29] = 0;
   out_298758434706635924[30] = 0;
   out_298758434706635924[31] = 1;
   out_298758434706635924[32] = 0;
   out_298758434706635924[33] = 0;
   out_298758434706635924[34] = 1;
   out_298758434706635924[35] = 0;
   out_298758434706635924[36] = 9.8100000000000005*sin(state[0])*cos(state[1]);
   out_298758434706635924[37] = 9.8100000000000005*sin(state[1])*cos(state[0]);
   out_298758434706635924[38] = 0;
   out_298758434706635924[39] = -state[7];
   out_298758434706635924[40] = state[6];
   out_298758434706635924[41] = 0;
   out_298758434706635924[42] = state[4];
   out_298758434706635924[43] = -state[3];
   out_298758434706635924[44] = 0;
   out_298758434706635924[45] = 0;
   out_298758434706635924[46] = 0;
   out_298758434706635924[47] = 0;
   out_298758434706635924[48] = 0;
   out_298758434706635924[49] = 0;
   out_298758434706635924[50] = 1;
   out_298758434706635924[51] = 0;
   out_298758434706635924[52] = 0;
   out_298758434706635924[53] = 1;
}
void h_13(double *state, double *unused, double *out_2632661140725285312) {
   out_2632661140725285312[0] = state[3];
   out_2632661140725285312[1] = state[4];
   out_2632661140725285312[2] = state[5];
}
void H_13(double *state, double *unused, double *out_8574336709255753324) {
   out_8574336709255753324[0] = 0;
   out_8574336709255753324[1] = 0;
   out_8574336709255753324[2] = 0;
   out_8574336709255753324[3] = 1;
   out_8574336709255753324[4] = 0;
   out_8574336709255753324[5] = 0;
   out_8574336709255753324[6] = 0;
   out_8574336709255753324[7] = 0;
   out_8574336709255753324[8] = 0;
   out_8574336709255753324[9] = 0;
   out_8574336709255753324[10] = 0;
   out_8574336709255753324[11] = 0;
   out_8574336709255753324[12] = 0;
   out_8574336709255753324[13] = 0;
   out_8574336709255753324[14] = 0;
   out_8574336709255753324[15] = 0;
   out_8574336709255753324[16] = 0;
   out_8574336709255753324[17] = 0;
   out_8574336709255753324[18] = 0;
   out_8574336709255753324[19] = 0;
   out_8574336709255753324[20] = 0;
   out_8574336709255753324[21] = 0;
   out_8574336709255753324[22] = 1;
   out_8574336709255753324[23] = 0;
   out_8574336709255753324[24] = 0;
   out_8574336709255753324[25] = 0;
   out_8574336709255753324[26] = 0;
   out_8574336709255753324[27] = 0;
   out_8574336709255753324[28] = 0;
   out_8574336709255753324[29] = 0;
   out_8574336709255753324[30] = 0;
   out_8574336709255753324[31] = 0;
   out_8574336709255753324[32] = 0;
   out_8574336709255753324[33] = 0;
   out_8574336709255753324[34] = 0;
   out_8574336709255753324[35] = 0;
   out_8574336709255753324[36] = 0;
   out_8574336709255753324[37] = 0;
   out_8574336709255753324[38] = 0;
   out_8574336709255753324[39] = 0;
   out_8574336709255753324[40] = 0;
   out_8574336709255753324[41] = 1;
   out_8574336709255753324[42] = 0;
   out_8574336709255753324[43] = 0;
   out_8574336709255753324[44] = 0;
   out_8574336709255753324[45] = 0;
   out_8574336709255753324[46] = 0;
   out_8574336709255753324[47] = 0;
   out_8574336709255753324[48] = 0;
   out_8574336709255753324[49] = 0;
   out_8574336709255753324[50] = 0;
   out_8574336709255753324[51] = 0;
   out_8574336709255753324[52] = 0;
   out_8574336709255753324[53] = 0;
}
void h_14(double *state, double *unused, double *out_8641500759550838094) {
   out_8641500759550838094[0] = state[6];
   out_8641500759550838094[1] = state[7];
   out_8641500759550838094[2] = state[8];
}
void H_14(double *state, double *unused, double *out_9121440333446646564) {
   out_9121440333446646564[0] = 0;
   out_9121440333446646564[1] = 0;
   out_9121440333446646564[2] = 0;
   out_9121440333446646564[3] = 0;
   out_9121440333446646564[4] = 0;
   out_9121440333446646564[5] = 0;
   out_9121440333446646564[6] = 1;
   out_9121440333446646564[7] = 0;
   out_9121440333446646564[8] = 0;
   out_9121440333446646564[9] = 0;
   out_9121440333446646564[10] = 0;
   out_9121440333446646564[11] = 0;
   out_9121440333446646564[12] = 0;
   out_9121440333446646564[13] = 0;
   out_9121440333446646564[14] = 0;
   out_9121440333446646564[15] = 0;
   out_9121440333446646564[16] = 0;
   out_9121440333446646564[17] = 0;
   out_9121440333446646564[18] = 0;
   out_9121440333446646564[19] = 0;
   out_9121440333446646564[20] = 0;
   out_9121440333446646564[21] = 0;
   out_9121440333446646564[22] = 0;
   out_9121440333446646564[23] = 0;
   out_9121440333446646564[24] = 0;
   out_9121440333446646564[25] = 1;
   out_9121440333446646564[26] = 0;
   out_9121440333446646564[27] = 0;
   out_9121440333446646564[28] = 0;
   out_9121440333446646564[29] = 0;
   out_9121440333446646564[30] = 0;
   out_9121440333446646564[31] = 0;
   out_9121440333446646564[32] = 0;
   out_9121440333446646564[33] = 0;
   out_9121440333446646564[34] = 0;
   out_9121440333446646564[35] = 0;
   out_9121440333446646564[36] = 0;
   out_9121440333446646564[37] = 0;
   out_9121440333446646564[38] = 0;
   out_9121440333446646564[39] = 0;
   out_9121440333446646564[40] = 0;
   out_9121440333446646564[41] = 0;
   out_9121440333446646564[42] = 0;
   out_9121440333446646564[43] = 0;
   out_9121440333446646564[44] = 1;
   out_9121440333446646564[45] = 0;
   out_9121440333446646564[46] = 0;
   out_9121440333446646564[47] = 0;
   out_9121440333446646564[48] = 0;
   out_9121440333446646564[49] = 0;
   out_9121440333446646564[50] = 0;
   out_9121440333446646564[51] = 0;
   out_9121440333446646564[52] = 0;
   out_9121440333446646564[53] = 0;
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
void pose_err_fun(double *nom_x, double *delta_x, double *out_3641871299484350556) {
  err_fun(nom_x, delta_x, out_3641871299484350556);
}
void pose_inv_err_fun(double *nom_x, double *true_x, double *out_3119284233878604394) {
  inv_err_fun(nom_x, true_x, out_3119284233878604394);
}
void pose_H_mod_fun(double *state, double *out_2783404226845349256) {
  H_mod_fun(state, out_2783404226845349256);
}
void pose_f_fun(double *state, double dt, double *out_5949144455846088993) {
  f_fun(state,  dt, out_5949144455846088993);
}
void pose_F_fun(double *state, double dt, double *out_7424333812317239085) {
  F_fun(state,  dt, out_7424333812317239085);
}
void pose_h_4(double *state, double *unused, double *out_8321002018191485436) {
  h_4(state, unused, out_8321002018191485436);
}
void pose_H_4(double *state, double *unused, double *out_5362062883923420523) {
  H_4(state, unused, out_5362062883923420523);
}
void pose_h_10(double *state, double *unused, double *out_2988408482111357830) {
  h_10(state, unused, out_2988408482111357830);
}
void pose_H_10(double *state, double *unused, double *out_298758434706635924) {
  H_10(state, unused, out_298758434706635924);
}
void pose_h_13(double *state, double *unused, double *out_2632661140725285312) {
  h_13(state, unused, out_2632661140725285312);
}
void pose_H_13(double *state, double *unused, double *out_8574336709255753324) {
  H_13(state, unused, out_8574336709255753324);
}
void pose_h_14(double *state, double *unused, double *out_8641500759550838094) {
  h_14(state, unused, out_8641500759550838094);
}
void pose_H_14(double *state, double *unused, double *out_9121440333446646564) {
  H_14(state, unused, out_9121440333446646564);
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
