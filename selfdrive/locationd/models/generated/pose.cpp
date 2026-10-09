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
void err_fun(double *nom_x, double *delta_x, double *out_731387772078245243) {
   out_731387772078245243[0] = delta_x[0] + nom_x[0];
   out_731387772078245243[1] = delta_x[1] + nom_x[1];
   out_731387772078245243[2] = delta_x[2] + nom_x[2];
   out_731387772078245243[3] = delta_x[3] + nom_x[3];
   out_731387772078245243[4] = delta_x[4] + nom_x[4];
   out_731387772078245243[5] = delta_x[5] + nom_x[5];
   out_731387772078245243[6] = delta_x[6] + nom_x[6];
   out_731387772078245243[7] = delta_x[7] + nom_x[7];
   out_731387772078245243[8] = delta_x[8] + nom_x[8];
   out_731387772078245243[9] = delta_x[9] + nom_x[9];
   out_731387772078245243[10] = delta_x[10] + nom_x[10];
   out_731387772078245243[11] = delta_x[11] + nom_x[11];
   out_731387772078245243[12] = delta_x[12] + nom_x[12];
   out_731387772078245243[13] = delta_x[13] + nom_x[13];
   out_731387772078245243[14] = delta_x[14] + nom_x[14];
   out_731387772078245243[15] = delta_x[15] + nom_x[15];
   out_731387772078245243[16] = delta_x[16] + nom_x[16];
   out_731387772078245243[17] = delta_x[17] + nom_x[17];
}
void inv_err_fun(double *nom_x, double *true_x, double *out_4206130707332622452) {
   out_4206130707332622452[0] = -nom_x[0] + true_x[0];
   out_4206130707332622452[1] = -nom_x[1] + true_x[1];
   out_4206130707332622452[2] = -nom_x[2] + true_x[2];
   out_4206130707332622452[3] = -nom_x[3] + true_x[3];
   out_4206130707332622452[4] = -nom_x[4] + true_x[4];
   out_4206130707332622452[5] = -nom_x[5] + true_x[5];
   out_4206130707332622452[6] = -nom_x[6] + true_x[6];
   out_4206130707332622452[7] = -nom_x[7] + true_x[7];
   out_4206130707332622452[8] = -nom_x[8] + true_x[8];
   out_4206130707332622452[9] = -nom_x[9] + true_x[9];
   out_4206130707332622452[10] = -nom_x[10] + true_x[10];
   out_4206130707332622452[11] = -nom_x[11] + true_x[11];
   out_4206130707332622452[12] = -nom_x[12] + true_x[12];
   out_4206130707332622452[13] = -nom_x[13] + true_x[13];
   out_4206130707332622452[14] = -nom_x[14] + true_x[14];
   out_4206130707332622452[15] = -nom_x[15] + true_x[15];
   out_4206130707332622452[16] = -nom_x[16] + true_x[16];
   out_4206130707332622452[17] = -nom_x[17] + true_x[17];
}
void H_mod_fun(double *state, double *out_2916011499501574438) {
   out_2916011499501574438[0] = 1.0;
   out_2916011499501574438[1] = 0.0;
   out_2916011499501574438[2] = 0.0;
   out_2916011499501574438[3] = 0.0;
   out_2916011499501574438[4] = 0.0;
   out_2916011499501574438[5] = 0.0;
   out_2916011499501574438[6] = 0.0;
   out_2916011499501574438[7] = 0.0;
   out_2916011499501574438[8] = 0.0;
   out_2916011499501574438[9] = 0.0;
   out_2916011499501574438[10] = 0.0;
   out_2916011499501574438[11] = 0.0;
   out_2916011499501574438[12] = 0.0;
   out_2916011499501574438[13] = 0.0;
   out_2916011499501574438[14] = 0.0;
   out_2916011499501574438[15] = 0.0;
   out_2916011499501574438[16] = 0.0;
   out_2916011499501574438[17] = 0.0;
   out_2916011499501574438[18] = 0.0;
   out_2916011499501574438[19] = 1.0;
   out_2916011499501574438[20] = 0.0;
   out_2916011499501574438[21] = 0.0;
   out_2916011499501574438[22] = 0.0;
   out_2916011499501574438[23] = 0.0;
   out_2916011499501574438[24] = 0.0;
   out_2916011499501574438[25] = 0.0;
   out_2916011499501574438[26] = 0.0;
   out_2916011499501574438[27] = 0.0;
   out_2916011499501574438[28] = 0.0;
   out_2916011499501574438[29] = 0.0;
   out_2916011499501574438[30] = 0.0;
   out_2916011499501574438[31] = 0.0;
   out_2916011499501574438[32] = 0.0;
   out_2916011499501574438[33] = 0.0;
   out_2916011499501574438[34] = 0.0;
   out_2916011499501574438[35] = 0.0;
   out_2916011499501574438[36] = 0.0;
   out_2916011499501574438[37] = 0.0;
   out_2916011499501574438[38] = 1.0;
   out_2916011499501574438[39] = 0.0;
   out_2916011499501574438[40] = 0.0;
   out_2916011499501574438[41] = 0.0;
   out_2916011499501574438[42] = 0.0;
   out_2916011499501574438[43] = 0.0;
   out_2916011499501574438[44] = 0.0;
   out_2916011499501574438[45] = 0.0;
   out_2916011499501574438[46] = 0.0;
   out_2916011499501574438[47] = 0.0;
   out_2916011499501574438[48] = 0.0;
   out_2916011499501574438[49] = 0.0;
   out_2916011499501574438[50] = 0.0;
   out_2916011499501574438[51] = 0.0;
   out_2916011499501574438[52] = 0.0;
   out_2916011499501574438[53] = 0.0;
   out_2916011499501574438[54] = 0.0;
   out_2916011499501574438[55] = 0.0;
   out_2916011499501574438[56] = 0.0;
   out_2916011499501574438[57] = 1.0;
   out_2916011499501574438[58] = 0.0;
   out_2916011499501574438[59] = 0.0;
   out_2916011499501574438[60] = 0.0;
   out_2916011499501574438[61] = 0.0;
   out_2916011499501574438[62] = 0.0;
   out_2916011499501574438[63] = 0.0;
   out_2916011499501574438[64] = 0.0;
   out_2916011499501574438[65] = 0.0;
   out_2916011499501574438[66] = 0.0;
   out_2916011499501574438[67] = 0.0;
   out_2916011499501574438[68] = 0.0;
   out_2916011499501574438[69] = 0.0;
   out_2916011499501574438[70] = 0.0;
   out_2916011499501574438[71] = 0.0;
   out_2916011499501574438[72] = 0.0;
   out_2916011499501574438[73] = 0.0;
   out_2916011499501574438[74] = 0.0;
   out_2916011499501574438[75] = 0.0;
   out_2916011499501574438[76] = 1.0;
   out_2916011499501574438[77] = 0.0;
   out_2916011499501574438[78] = 0.0;
   out_2916011499501574438[79] = 0.0;
   out_2916011499501574438[80] = 0.0;
   out_2916011499501574438[81] = 0.0;
   out_2916011499501574438[82] = 0.0;
   out_2916011499501574438[83] = 0.0;
   out_2916011499501574438[84] = 0.0;
   out_2916011499501574438[85] = 0.0;
   out_2916011499501574438[86] = 0.0;
   out_2916011499501574438[87] = 0.0;
   out_2916011499501574438[88] = 0.0;
   out_2916011499501574438[89] = 0.0;
   out_2916011499501574438[90] = 0.0;
   out_2916011499501574438[91] = 0.0;
   out_2916011499501574438[92] = 0.0;
   out_2916011499501574438[93] = 0.0;
   out_2916011499501574438[94] = 0.0;
   out_2916011499501574438[95] = 1.0;
   out_2916011499501574438[96] = 0.0;
   out_2916011499501574438[97] = 0.0;
   out_2916011499501574438[98] = 0.0;
   out_2916011499501574438[99] = 0.0;
   out_2916011499501574438[100] = 0.0;
   out_2916011499501574438[101] = 0.0;
   out_2916011499501574438[102] = 0.0;
   out_2916011499501574438[103] = 0.0;
   out_2916011499501574438[104] = 0.0;
   out_2916011499501574438[105] = 0.0;
   out_2916011499501574438[106] = 0.0;
   out_2916011499501574438[107] = 0.0;
   out_2916011499501574438[108] = 0.0;
   out_2916011499501574438[109] = 0.0;
   out_2916011499501574438[110] = 0.0;
   out_2916011499501574438[111] = 0.0;
   out_2916011499501574438[112] = 0.0;
   out_2916011499501574438[113] = 0.0;
   out_2916011499501574438[114] = 1.0;
   out_2916011499501574438[115] = 0.0;
   out_2916011499501574438[116] = 0.0;
   out_2916011499501574438[117] = 0.0;
   out_2916011499501574438[118] = 0.0;
   out_2916011499501574438[119] = 0.0;
   out_2916011499501574438[120] = 0.0;
   out_2916011499501574438[121] = 0.0;
   out_2916011499501574438[122] = 0.0;
   out_2916011499501574438[123] = 0.0;
   out_2916011499501574438[124] = 0.0;
   out_2916011499501574438[125] = 0.0;
   out_2916011499501574438[126] = 0.0;
   out_2916011499501574438[127] = 0.0;
   out_2916011499501574438[128] = 0.0;
   out_2916011499501574438[129] = 0.0;
   out_2916011499501574438[130] = 0.0;
   out_2916011499501574438[131] = 0.0;
   out_2916011499501574438[132] = 0.0;
   out_2916011499501574438[133] = 1.0;
   out_2916011499501574438[134] = 0.0;
   out_2916011499501574438[135] = 0.0;
   out_2916011499501574438[136] = 0.0;
   out_2916011499501574438[137] = 0.0;
   out_2916011499501574438[138] = 0.0;
   out_2916011499501574438[139] = 0.0;
   out_2916011499501574438[140] = 0.0;
   out_2916011499501574438[141] = 0.0;
   out_2916011499501574438[142] = 0.0;
   out_2916011499501574438[143] = 0.0;
   out_2916011499501574438[144] = 0.0;
   out_2916011499501574438[145] = 0.0;
   out_2916011499501574438[146] = 0.0;
   out_2916011499501574438[147] = 0.0;
   out_2916011499501574438[148] = 0.0;
   out_2916011499501574438[149] = 0.0;
   out_2916011499501574438[150] = 0.0;
   out_2916011499501574438[151] = 0.0;
   out_2916011499501574438[152] = 1.0;
   out_2916011499501574438[153] = 0.0;
   out_2916011499501574438[154] = 0.0;
   out_2916011499501574438[155] = 0.0;
   out_2916011499501574438[156] = 0.0;
   out_2916011499501574438[157] = 0.0;
   out_2916011499501574438[158] = 0.0;
   out_2916011499501574438[159] = 0.0;
   out_2916011499501574438[160] = 0.0;
   out_2916011499501574438[161] = 0.0;
   out_2916011499501574438[162] = 0.0;
   out_2916011499501574438[163] = 0.0;
   out_2916011499501574438[164] = 0.0;
   out_2916011499501574438[165] = 0.0;
   out_2916011499501574438[166] = 0.0;
   out_2916011499501574438[167] = 0.0;
   out_2916011499501574438[168] = 0.0;
   out_2916011499501574438[169] = 0.0;
   out_2916011499501574438[170] = 0.0;
   out_2916011499501574438[171] = 1.0;
   out_2916011499501574438[172] = 0.0;
   out_2916011499501574438[173] = 0.0;
   out_2916011499501574438[174] = 0.0;
   out_2916011499501574438[175] = 0.0;
   out_2916011499501574438[176] = 0.0;
   out_2916011499501574438[177] = 0.0;
   out_2916011499501574438[178] = 0.0;
   out_2916011499501574438[179] = 0.0;
   out_2916011499501574438[180] = 0.0;
   out_2916011499501574438[181] = 0.0;
   out_2916011499501574438[182] = 0.0;
   out_2916011499501574438[183] = 0.0;
   out_2916011499501574438[184] = 0.0;
   out_2916011499501574438[185] = 0.0;
   out_2916011499501574438[186] = 0.0;
   out_2916011499501574438[187] = 0.0;
   out_2916011499501574438[188] = 0.0;
   out_2916011499501574438[189] = 0.0;
   out_2916011499501574438[190] = 1.0;
   out_2916011499501574438[191] = 0.0;
   out_2916011499501574438[192] = 0.0;
   out_2916011499501574438[193] = 0.0;
   out_2916011499501574438[194] = 0.0;
   out_2916011499501574438[195] = 0.0;
   out_2916011499501574438[196] = 0.0;
   out_2916011499501574438[197] = 0.0;
   out_2916011499501574438[198] = 0.0;
   out_2916011499501574438[199] = 0.0;
   out_2916011499501574438[200] = 0.0;
   out_2916011499501574438[201] = 0.0;
   out_2916011499501574438[202] = 0.0;
   out_2916011499501574438[203] = 0.0;
   out_2916011499501574438[204] = 0.0;
   out_2916011499501574438[205] = 0.0;
   out_2916011499501574438[206] = 0.0;
   out_2916011499501574438[207] = 0.0;
   out_2916011499501574438[208] = 0.0;
   out_2916011499501574438[209] = 1.0;
   out_2916011499501574438[210] = 0.0;
   out_2916011499501574438[211] = 0.0;
   out_2916011499501574438[212] = 0.0;
   out_2916011499501574438[213] = 0.0;
   out_2916011499501574438[214] = 0.0;
   out_2916011499501574438[215] = 0.0;
   out_2916011499501574438[216] = 0.0;
   out_2916011499501574438[217] = 0.0;
   out_2916011499501574438[218] = 0.0;
   out_2916011499501574438[219] = 0.0;
   out_2916011499501574438[220] = 0.0;
   out_2916011499501574438[221] = 0.0;
   out_2916011499501574438[222] = 0.0;
   out_2916011499501574438[223] = 0.0;
   out_2916011499501574438[224] = 0.0;
   out_2916011499501574438[225] = 0.0;
   out_2916011499501574438[226] = 0.0;
   out_2916011499501574438[227] = 0.0;
   out_2916011499501574438[228] = 1.0;
   out_2916011499501574438[229] = 0.0;
   out_2916011499501574438[230] = 0.0;
   out_2916011499501574438[231] = 0.0;
   out_2916011499501574438[232] = 0.0;
   out_2916011499501574438[233] = 0.0;
   out_2916011499501574438[234] = 0.0;
   out_2916011499501574438[235] = 0.0;
   out_2916011499501574438[236] = 0.0;
   out_2916011499501574438[237] = 0.0;
   out_2916011499501574438[238] = 0.0;
   out_2916011499501574438[239] = 0.0;
   out_2916011499501574438[240] = 0.0;
   out_2916011499501574438[241] = 0.0;
   out_2916011499501574438[242] = 0.0;
   out_2916011499501574438[243] = 0.0;
   out_2916011499501574438[244] = 0.0;
   out_2916011499501574438[245] = 0.0;
   out_2916011499501574438[246] = 0.0;
   out_2916011499501574438[247] = 1.0;
   out_2916011499501574438[248] = 0.0;
   out_2916011499501574438[249] = 0.0;
   out_2916011499501574438[250] = 0.0;
   out_2916011499501574438[251] = 0.0;
   out_2916011499501574438[252] = 0.0;
   out_2916011499501574438[253] = 0.0;
   out_2916011499501574438[254] = 0.0;
   out_2916011499501574438[255] = 0.0;
   out_2916011499501574438[256] = 0.0;
   out_2916011499501574438[257] = 0.0;
   out_2916011499501574438[258] = 0.0;
   out_2916011499501574438[259] = 0.0;
   out_2916011499501574438[260] = 0.0;
   out_2916011499501574438[261] = 0.0;
   out_2916011499501574438[262] = 0.0;
   out_2916011499501574438[263] = 0.0;
   out_2916011499501574438[264] = 0.0;
   out_2916011499501574438[265] = 0.0;
   out_2916011499501574438[266] = 1.0;
   out_2916011499501574438[267] = 0.0;
   out_2916011499501574438[268] = 0.0;
   out_2916011499501574438[269] = 0.0;
   out_2916011499501574438[270] = 0.0;
   out_2916011499501574438[271] = 0.0;
   out_2916011499501574438[272] = 0.0;
   out_2916011499501574438[273] = 0.0;
   out_2916011499501574438[274] = 0.0;
   out_2916011499501574438[275] = 0.0;
   out_2916011499501574438[276] = 0.0;
   out_2916011499501574438[277] = 0.0;
   out_2916011499501574438[278] = 0.0;
   out_2916011499501574438[279] = 0.0;
   out_2916011499501574438[280] = 0.0;
   out_2916011499501574438[281] = 0.0;
   out_2916011499501574438[282] = 0.0;
   out_2916011499501574438[283] = 0.0;
   out_2916011499501574438[284] = 0.0;
   out_2916011499501574438[285] = 1.0;
   out_2916011499501574438[286] = 0.0;
   out_2916011499501574438[287] = 0.0;
   out_2916011499501574438[288] = 0.0;
   out_2916011499501574438[289] = 0.0;
   out_2916011499501574438[290] = 0.0;
   out_2916011499501574438[291] = 0.0;
   out_2916011499501574438[292] = 0.0;
   out_2916011499501574438[293] = 0.0;
   out_2916011499501574438[294] = 0.0;
   out_2916011499501574438[295] = 0.0;
   out_2916011499501574438[296] = 0.0;
   out_2916011499501574438[297] = 0.0;
   out_2916011499501574438[298] = 0.0;
   out_2916011499501574438[299] = 0.0;
   out_2916011499501574438[300] = 0.0;
   out_2916011499501574438[301] = 0.0;
   out_2916011499501574438[302] = 0.0;
   out_2916011499501574438[303] = 0.0;
   out_2916011499501574438[304] = 1.0;
   out_2916011499501574438[305] = 0.0;
   out_2916011499501574438[306] = 0.0;
   out_2916011499501574438[307] = 0.0;
   out_2916011499501574438[308] = 0.0;
   out_2916011499501574438[309] = 0.0;
   out_2916011499501574438[310] = 0.0;
   out_2916011499501574438[311] = 0.0;
   out_2916011499501574438[312] = 0.0;
   out_2916011499501574438[313] = 0.0;
   out_2916011499501574438[314] = 0.0;
   out_2916011499501574438[315] = 0.0;
   out_2916011499501574438[316] = 0.0;
   out_2916011499501574438[317] = 0.0;
   out_2916011499501574438[318] = 0.0;
   out_2916011499501574438[319] = 0.0;
   out_2916011499501574438[320] = 0.0;
   out_2916011499501574438[321] = 0.0;
   out_2916011499501574438[322] = 0.0;
   out_2916011499501574438[323] = 1.0;
}
void f_fun(double *state, double dt, double *out_4420889553799640425) {
   out_4420889553799640425[0] = atan2((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), -(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]));
   out_4420889553799640425[1] = asin(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]));
   out_4420889553799640425[2] = atan2(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), -(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]));
   out_4420889553799640425[3] = dt*state[12] + state[3];
   out_4420889553799640425[4] = dt*state[13] + state[4];
   out_4420889553799640425[5] = dt*state[14] + state[5];
   out_4420889553799640425[6] = state[6];
   out_4420889553799640425[7] = state[7];
   out_4420889553799640425[8] = state[8];
   out_4420889553799640425[9] = state[9];
   out_4420889553799640425[10] = state[10];
   out_4420889553799640425[11] = state[11];
   out_4420889553799640425[12] = state[12];
   out_4420889553799640425[13] = state[13];
   out_4420889553799640425[14] = state[14];
   out_4420889553799640425[15] = state[15];
   out_4420889553799640425[16] = state[16];
   out_4420889553799640425[17] = state[17];
}
void F_fun(double *state, double dt, double *out_586752082486093199) {
   out_586752082486093199[0] = ((-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*cos(state[0])*cos(state[1]) - sin(state[0])*cos(dt*state[6])*cos(dt*state[7])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + ((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*cos(state[0])*cos(state[1]) - sin(dt*state[6])*sin(state[0])*cos(dt*state[7])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_586752082486093199[1] = ((-sin(dt*state[6])*sin(dt*state[8]) - sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*cos(state[1]) - (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*sin(state[1]) - sin(state[1])*cos(dt*state[6])*cos(dt*state[7])*cos(state[0]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*sin(state[1]) + (-sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) + sin(dt*state[8])*cos(dt*state[6]))*cos(state[1]) - sin(dt*state[6])*sin(state[1])*cos(dt*state[7])*cos(state[0]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_586752082486093199[2] = 0;
   out_586752082486093199[3] = 0;
   out_586752082486093199[4] = 0;
   out_586752082486093199[5] = 0;
   out_586752082486093199[6] = (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(dt*cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*sin(dt*state[8]) - dt*sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-dt*sin(dt*state[6])*cos(dt*state[8]) + dt*sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) - dt*cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (dt*sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_586752082486093199[7] = (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[6])*sin(dt*state[7])*cos(state[0])*cos(state[1]) + dt*sin(dt*state[6])*sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) - dt*sin(dt*state[6])*sin(state[1])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[7])*cos(dt*state[6])*cos(state[0])*cos(state[1]) + dt*sin(dt*state[8])*sin(state[0])*cos(dt*state[6])*cos(dt*state[7])*cos(state[1]) - dt*sin(state[1])*cos(dt*state[6])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_586752082486093199[8] = ((dt*sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + dt*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (dt*sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + ((dt*sin(dt*state[6])*sin(dt*state[8]) + dt*sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*cos(dt*state[8]) + dt*sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_586752082486093199[9] = 0;
   out_586752082486093199[10] = 0;
   out_586752082486093199[11] = 0;
   out_586752082486093199[12] = 0;
   out_586752082486093199[13] = 0;
   out_586752082486093199[14] = 0;
   out_586752082486093199[15] = 0;
   out_586752082486093199[16] = 0;
   out_586752082486093199[17] = 0;
   out_586752082486093199[18] = (-sin(dt*state[7])*sin(state[0])*cos(state[1]) - sin(dt*state[8])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_586752082486093199[19] = (-sin(dt*state[7])*sin(state[1])*cos(state[0]) + sin(dt*state[8])*sin(state[0])*sin(state[1])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_586752082486093199[20] = 0;
   out_586752082486093199[21] = 0;
   out_586752082486093199[22] = 0;
   out_586752082486093199[23] = 0;
   out_586752082486093199[24] = 0;
   out_586752082486093199[25] = (dt*sin(dt*state[7])*sin(dt*state[8])*sin(state[0])*cos(state[1]) - dt*sin(dt*state[7])*sin(state[1])*cos(dt*state[8]) + dt*cos(dt*state[7])*cos(state[0])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_586752082486093199[26] = (-dt*sin(dt*state[8])*sin(state[1])*cos(dt*state[7]) - dt*sin(state[0])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_586752082486093199[27] = 0;
   out_586752082486093199[28] = 0;
   out_586752082486093199[29] = 0;
   out_586752082486093199[30] = 0;
   out_586752082486093199[31] = 0;
   out_586752082486093199[32] = 0;
   out_586752082486093199[33] = 0;
   out_586752082486093199[34] = 0;
   out_586752082486093199[35] = 0;
   out_586752082486093199[36] = ((sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[7]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[7]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_586752082486093199[37] = (-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(-sin(dt*state[7])*sin(state[2])*cos(state[0])*cos(state[1]) + sin(dt*state[8])*sin(state[0])*sin(state[2])*cos(dt*state[7])*cos(state[1]) - sin(state[1])*sin(state[2])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*(-sin(dt*state[7])*cos(state[0])*cos(state[1])*cos(state[2]) + sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1])*cos(state[2]) - sin(state[1])*cos(dt*state[7])*cos(dt*state[8])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_586752082486093199[38] = ((-sin(state[0])*sin(state[2]) - sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (-sin(state[0])*sin(state[1])*sin(state[2]) - cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_586752082486093199[39] = 0;
   out_586752082486093199[40] = 0;
   out_586752082486093199[41] = 0;
   out_586752082486093199[42] = 0;
   out_586752082486093199[43] = (-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(dt*(sin(state[0])*cos(state[2]) - sin(state[1])*sin(state[2])*cos(state[0]))*cos(dt*state[7]) - dt*(sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[7])*sin(dt*state[8]) - dt*sin(dt*state[7])*sin(state[2])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*(dt*(-sin(state[0])*sin(state[2]) - sin(state[1])*cos(state[0])*cos(state[2]))*cos(dt*state[7]) - dt*(sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[7])*sin(dt*state[8]) - dt*sin(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_586752082486093199[44] = (dt*(sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*cos(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*sin(state[2])*cos(dt*state[7])*cos(state[1]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + (dt*(sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*cos(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[7])*cos(state[1])*cos(state[2]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_586752082486093199[45] = 0;
   out_586752082486093199[46] = 0;
   out_586752082486093199[47] = 0;
   out_586752082486093199[48] = 0;
   out_586752082486093199[49] = 0;
   out_586752082486093199[50] = 0;
   out_586752082486093199[51] = 0;
   out_586752082486093199[52] = 0;
   out_586752082486093199[53] = 0;
   out_586752082486093199[54] = 0;
   out_586752082486093199[55] = 0;
   out_586752082486093199[56] = 0;
   out_586752082486093199[57] = 1;
   out_586752082486093199[58] = 0;
   out_586752082486093199[59] = 0;
   out_586752082486093199[60] = 0;
   out_586752082486093199[61] = 0;
   out_586752082486093199[62] = 0;
   out_586752082486093199[63] = 0;
   out_586752082486093199[64] = 0;
   out_586752082486093199[65] = 0;
   out_586752082486093199[66] = dt;
   out_586752082486093199[67] = 0;
   out_586752082486093199[68] = 0;
   out_586752082486093199[69] = 0;
   out_586752082486093199[70] = 0;
   out_586752082486093199[71] = 0;
   out_586752082486093199[72] = 0;
   out_586752082486093199[73] = 0;
   out_586752082486093199[74] = 0;
   out_586752082486093199[75] = 0;
   out_586752082486093199[76] = 1;
   out_586752082486093199[77] = 0;
   out_586752082486093199[78] = 0;
   out_586752082486093199[79] = 0;
   out_586752082486093199[80] = 0;
   out_586752082486093199[81] = 0;
   out_586752082486093199[82] = 0;
   out_586752082486093199[83] = 0;
   out_586752082486093199[84] = 0;
   out_586752082486093199[85] = dt;
   out_586752082486093199[86] = 0;
   out_586752082486093199[87] = 0;
   out_586752082486093199[88] = 0;
   out_586752082486093199[89] = 0;
   out_586752082486093199[90] = 0;
   out_586752082486093199[91] = 0;
   out_586752082486093199[92] = 0;
   out_586752082486093199[93] = 0;
   out_586752082486093199[94] = 0;
   out_586752082486093199[95] = 1;
   out_586752082486093199[96] = 0;
   out_586752082486093199[97] = 0;
   out_586752082486093199[98] = 0;
   out_586752082486093199[99] = 0;
   out_586752082486093199[100] = 0;
   out_586752082486093199[101] = 0;
   out_586752082486093199[102] = 0;
   out_586752082486093199[103] = 0;
   out_586752082486093199[104] = dt;
   out_586752082486093199[105] = 0;
   out_586752082486093199[106] = 0;
   out_586752082486093199[107] = 0;
   out_586752082486093199[108] = 0;
   out_586752082486093199[109] = 0;
   out_586752082486093199[110] = 0;
   out_586752082486093199[111] = 0;
   out_586752082486093199[112] = 0;
   out_586752082486093199[113] = 0;
   out_586752082486093199[114] = 1;
   out_586752082486093199[115] = 0;
   out_586752082486093199[116] = 0;
   out_586752082486093199[117] = 0;
   out_586752082486093199[118] = 0;
   out_586752082486093199[119] = 0;
   out_586752082486093199[120] = 0;
   out_586752082486093199[121] = 0;
   out_586752082486093199[122] = 0;
   out_586752082486093199[123] = 0;
   out_586752082486093199[124] = 0;
   out_586752082486093199[125] = 0;
   out_586752082486093199[126] = 0;
   out_586752082486093199[127] = 0;
   out_586752082486093199[128] = 0;
   out_586752082486093199[129] = 0;
   out_586752082486093199[130] = 0;
   out_586752082486093199[131] = 0;
   out_586752082486093199[132] = 0;
   out_586752082486093199[133] = 1;
   out_586752082486093199[134] = 0;
   out_586752082486093199[135] = 0;
   out_586752082486093199[136] = 0;
   out_586752082486093199[137] = 0;
   out_586752082486093199[138] = 0;
   out_586752082486093199[139] = 0;
   out_586752082486093199[140] = 0;
   out_586752082486093199[141] = 0;
   out_586752082486093199[142] = 0;
   out_586752082486093199[143] = 0;
   out_586752082486093199[144] = 0;
   out_586752082486093199[145] = 0;
   out_586752082486093199[146] = 0;
   out_586752082486093199[147] = 0;
   out_586752082486093199[148] = 0;
   out_586752082486093199[149] = 0;
   out_586752082486093199[150] = 0;
   out_586752082486093199[151] = 0;
   out_586752082486093199[152] = 1;
   out_586752082486093199[153] = 0;
   out_586752082486093199[154] = 0;
   out_586752082486093199[155] = 0;
   out_586752082486093199[156] = 0;
   out_586752082486093199[157] = 0;
   out_586752082486093199[158] = 0;
   out_586752082486093199[159] = 0;
   out_586752082486093199[160] = 0;
   out_586752082486093199[161] = 0;
   out_586752082486093199[162] = 0;
   out_586752082486093199[163] = 0;
   out_586752082486093199[164] = 0;
   out_586752082486093199[165] = 0;
   out_586752082486093199[166] = 0;
   out_586752082486093199[167] = 0;
   out_586752082486093199[168] = 0;
   out_586752082486093199[169] = 0;
   out_586752082486093199[170] = 0;
   out_586752082486093199[171] = 1;
   out_586752082486093199[172] = 0;
   out_586752082486093199[173] = 0;
   out_586752082486093199[174] = 0;
   out_586752082486093199[175] = 0;
   out_586752082486093199[176] = 0;
   out_586752082486093199[177] = 0;
   out_586752082486093199[178] = 0;
   out_586752082486093199[179] = 0;
   out_586752082486093199[180] = 0;
   out_586752082486093199[181] = 0;
   out_586752082486093199[182] = 0;
   out_586752082486093199[183] = 0;
   out_586752082486093199[184] = 0;
   out_586752082486093199[185] = 0;
   out_586752082486093199[186] = 0;
   out_586752082486093199[187] = 0;
   out_586752082486093199[188] = 0;
   out_586752082486093199[189] = 0;
   out_586752082486093199[190] = 1;
   out_586752082486093199[191] = 0;
   out_586752082486093199[192] = 0;
   out_586752082486093199[193] = 0;
   out_586752082486093199[194] = 0;
   out_586752082486093199[195] = 0;
   out_586752082486093199[196] = 0;
   out_586752082486093199[197] = 0;
   out_586752082486093199[198] = 0;
   out_586752082486093199[199] = 0;
   out_586752082486093199[200] = 0;
   out_586752082486093199[201] = 0;
   out_586752082486093199[202] = 0;
   out_586752082486093199[203] = 0;
   out_586752082486093199[204] = 0;
   out_586752082486093199[205] = 0;
   out_586752082486093199[206] = 0;
   out_586752082486093199[207] = 0;
   out_586752082486093199[208] = 0;
   out_586752082486093199[209] = 1;
   out_586752082486093199[210] = 0;
   out_586752082486093199[211] = 0;
   out_586752082486093199[212] = 0;
   out_586752082486093199[213] = 0;
   out_586752082486093199[214] = 0;
   out_586752082486093199[215] = 0;
   out_586752082486093199[216] = 0;
   out_586752082486093199[217] = 0;
   out_586752082486093199[218] = 0;
   out_586752082486093199[219] = 0;
   out_586752082486093199[220] = 0;
   out_586752082486093199[221] = 0;
   out_586752082486093199[222] = 0;
   out_586752082486093199[223] = 0;
   out_586752082486093199[224] = 0;
   out_586752082486093199[225] = 0;
   out_586752082486093199[226] = 0;
   out_586752082486093199[227] = 0;
   out_586752082486093199[228] = 1;
   out_586752082486093199[229] = 0;
   out_586752082486093199[230] = 0;
   out_586752082486093199[231] = 0;
   out_586752082486093199[232] = 0;
   out_586752082486093199[233] = 0;
   out_586752082486093199[234] = 0;
   out_586752082486093199[235] = 0;
   out_586752082486093199[236] = 0;
   out_586752082486093199[237] = 0;
   out_586752082486093199[238] = 0;
   out_586752082486093199[239] = 0;
   out_586752082486093199[240] = 0;
   out_586752082486093199[241] = 0;
   out_586752082486093199[242] = 0;
   out_586752082486093199[243] = 0;
   out_586752082486093199[244] = 0;
   out_586752082486093199[245] = 0;
   out_586752082486093199[246] = 0;
   out_586752082486093199[247] = 1;
   out_586752082486093199[248] = 0;
   out_586752082486093199[249] = 0;
   out_586752082486093199[250] = 0;
   out_586752082486093199[251] = 0;
   out_586752082486093199[252] = 0;
   out_586752082486093199[253] = 0;
   out_586752082486093199[254] = 0;
   out_586752082486093199[255] = 0;
   out_586752082486093199[256] = 0;
   out_586752082486093199[257] = 0;
   out_586752082486093199[258] = 0;
   out_586752082486093199[259] = 0;
   out_586752082486093199[260] = 0;
   out_586752082486093199[261] = 0;
   out_586752082486093199[262] = 0;
   out_586752082486093199[263] = 0;
   out_586752082486093199[264] = 0;
   out_586752082486093199[265] = 0;
   out_586752082486093199[266] = 1;
   out_586752082486093199[267] = 0;
   out_586752082486093199[268] = 0;
   out_586752082486093199[269] = 0;
   out_586752082486093199[270] = 0;
   out_586752082486093199[271] = 0;
   out_586752082486093199[272] = 0;
   out_586752082486093199[273] = 0;
   out_586752082486093199[274] = 0;
   out_586752082486093199[275] = 0;
   out_586752082486093199[276] = 0;
   out_586752082486093199[277] = 0;
   out_586752082486093199[278] = 0;
   out_586752082486093199[279] = 0;
   out_586752082486093199[280] = 0;
   out_586752082486093199[281] = 0;
   out_586752082486093199[282] = 0;
   out_586752082486093199[283] = 0;
   out_586752082486093199[284] = 0;
   out_586752082486093199[285] = 1;
   out_586752082486093199[286] = 0;
   out_586752082486093199[287] = 0;
   out_586752082486093199[288] = 0;
   out_586752082486093199[289] = 0;
   out_586752082486093199[290] = 0;
   out_586752082486093199[291] = 0;
   out_586752082486093199[292] = 0;
   out_586752082486093199[293] = 0;
   out_586752082486093199[294] = 0;
   out_586752082486093199[295] = 0;
   out_586752082486093199[296] = 0;
   out_586752082486093199[297] = 0;
   out_586752082486093199[298] = 0;
   out_586752082486093199[299] = 0;
   out_586752082486093199[300] = 0;
   out_586752082486093199[301] = 0;
   out_586752082486093199[302] = 0;
   out_586752082486093199[303] = 0;
   out_586752082486093199[304] = 1;
   out_586752082486093199[305] = 0;
   out_586752082486093199[306] = 0;
   out_586752082486093199[307] = 0;
   out_586752082486093199[308] = 0;
   out_586752082486093199[309] = 0;
   out_586752082486093199[310] = 0;
   out_586752082486093199[311] = 0;
   out_586752082486093199[312] = 0;
   out_586752082486093199[313] = 0;
   out_586752082486093199[314] = 0;
   out_586752082486093199[315] = 0;
   out_586752082486093199[316] = 0;
   out_586752082486093199[317] = 0;
   out_586752082486093199[318] = 0;
   out_586752082486093199[319] = 0;
   out_586752082486093199[320] = 0;
   out_586752082486093199[321] = 0;
   out_586752082486093199[322] = 0;
   out_586752082486093199[323] = 1;
}
void h_4(double *state, double *unused, double *out_1330626957984611772) {
   out_1330626957984611772[0] = state[6] + state[9];
   out_1330626957984611772[1] = state[7] + state[10];
   out_1330626957984611772[2] = state[8] + state[11];
}
void H_4(double *state, double *unused, double *out_8068529884540655173) {
   out_8068529884540655173[0] = 0;
   out_8068529884540655173[1] = 0;
   out_8068529884540655173[2] = 0;
   out_8068529884540655173[3] = 0;
   out_8068529884540655173[4] = 0;
   out_8068529884540655173[5] = 0;
   out_8068529884540655173[6] = 1;
   out_8068529884540655173[7] = 0;
   out_8068529884540655173[8] = 0;
   out_8068529884540655173[9] = 1;
   out_8068529884540655173[10] = 0;
   out_8068529884540655173[11] = 0;
   out_8068529884540655173[12] = 0;
   out_8068529884540655173[13] = 0;
   out_8068529884540655173[14] = 0;
   out_8068529884540655173[15] = 0;
   out_8068529884540655173[16] = 0;
   out_8068529884540655173[17] = 0;
   out_8068529884540655173[18] = 0;
   out_8068529884540655173[19] = 0;
   out_8068529884540655173[20] = 0;
   out_8068529884540655173[21] = 0;
   out_8068529884540655173[22] = 0;
   out_8068529884540655173[23] = 0;
   out_8068529884540655173[24] = 0;
   out_8068529884540655173[25] = 1;
   out_8068529884540655173[26] = 0;
   out_8068529884540655173[27] = 0;
   out_8068529884540655173[28] = 1;
   out_8068529884540655173[29] = 0;
   out_8068529884540655173[30] = 0;
   out_8068529884540655173[31] = 0;
   out_8068529884540655173[32] = 0;
   out_8068529884540655173[33] = 0;
   out_8068529884540655173[34] = 0;
   out_8068529884540655173[35] = 0;
   out_8068529884540655173[36] = 0;
   out_8068529884540655173[37] = 0;
   out_8068529884540655173[38] = 0;
   out_8068529884540655173[39] = 0;
   out_8068529884540655173[40] = 0;
   out_8068529884540655173[41] = 0;
   out_8068529884540655173[42] = 0;
   out_8068529884540655173[43] = 0;
   out_8068529884540655173[44] = 1;
   out_8068529884540655173[45] = 0;
   out_8068529884540655173[46] = 0;
   out_8068529884540655173[47] = 1;
   out_8068529884540655173[48] = 0;
   out_8068529884540655173[49] = 0;
   out_8068529884540655173[50] = 0;
   out_8068529884540655173[51] = 0;
   out_8068529884540655173[52] = 0;
   out_8068529884540655173[53] = 0;
}
void h_10(double *state, double *unused, double *out_5440536108172962293) {
   out_5440536108172962293[0] = 9.8100000000000005*sin(state[1]) - state[4]*state[8] + state[5]*state[7] + state[12] + state[15];
   out_5440536108172962293[1] = -9.8100000000000005*sin(state[0])*cos(state[1]) + state[3]*state[8] - state[5]*state[6] + state[13] + state[16];
   out_5440536108172962293[2] = -9.8100000000000005*cos(state[0])*cos(state[1]) - state[3]*state[7] + state[4]*state[6] + state[14] + state[17];
}
void H_10(double *state, double *unused, double *out_3777395375513848052) {
   out_3777395375513848052[0] = 0;
   out_3777395375513848052[1] = 9.8100000000000005*cos(state[1]);
   out_3777395375513848052[2] = 0;
   out_3777395375513848052[3] = 0;
   out_3777395375513848052[4] = -state[8];
   out_3777395375513848052[5] = state[7];
   out_3777395375513848052[6] = 0;
   out_3777395375513848052[7] = state[5];
   out_3777395375513848052[8] = -state[4];
   out_3777395375513848052[9] = 0;
   out_3777395375513848052[10] = 0;
   out_3777395375513848052[11] = 0;
   out_3777395375513848052[12] = 1;
   out_3777395375513848052[13] = 0;
   out_3777395375513848052[14] = 0;
   out_3777395375513848052[15] = 1;
   out_3777395375513848052[16] = 0;
   out_3777395375513848052[17] = 0;
   out_3777395375513848052[18] = -9.8100000000000005*cos(state[0])*cos(state[1]);
   out_3777395375513848052[19] = 9.8100000000000005*sin(state[0])*sin(state[1]);
   out_3777395375513848052[20] = 0;
   out_3777395375513848052[21] = state[8];
   out_3777395375513848052[22] = 0;
   out_3777395375513848052[23] = -state[6];
   out_3777395375513848052[24] = -state[5];
   out_3777395375513848052[25] = 0;
   out_3777395375513848052[26] = state[3];
   out_3777395375513848052[27] = 0;
   out_3777395375513848052[28] = 0;
   out_3777395375513848052[29] = 0;
   out_3777395375513848052[30] = 0;
   out_3777395375513848052[31] = 1;
   out_3777395375513848052[32] = 0;
   out_3777395375513848052[33] = 0;
   out_3777395375513848052[34] = 1;
   out_3777395375513848052[35] = 0;
   out_3777395375513848052[36] = 9.8100000000000005*sin(state[0])*cos(state[1]);
   out_3777395375513848052[37] = 9.8100000000000005*sin(state[1])*cos(state[0]);
   out_3777395375513848052[38] = 0;
   out_3777395375513848052[39] = -state[7];
   out_3777395375513848052[40] = state[6];
   out_3777395375513848052[41] = 0;
   out_3777395375513848052[42] = state[4];
   out_3777395375513848052[43] = -state[3];
   out_3777395375513848052[44] = 0;
   out_3777395375513848052[45] = 0;
   out_3777395375513848052[46] = 0;
   out_3777395375513848052[47] = 0;
   out_3777395375513848052[48] = 0;
   out_3777395375513848052[49] = 0;
   out_3777395375513848052[50] = 1;
   out_3777395375513848052[51] = 0;
   out_3777395375513848052[52] = 0;
   out_3777395375513848052[53] = 1;
}
void h_13(double *state, double *unused, double *out_7911476404081815631) {
   out_7911476404081815631[0] = state[3];
   out_7911476404081815631[1] = state[4];
   out_7911476404081815631[2] = state[5];
}
void H_13(double *state, double *unused, double *out_7165940363836563642) {
   out_7165940363836563642[0] = 0;
   out_7165940363836563642[1] = 0;
   out_7165940363836563642[2] = 0;
   out_7165940363836563642[3] = 1;
   out_7165940363836563642[4] = 0;
   out_7165940363836563642[5] = 0;
   out_7165940363836563642[6] = 0;
   out_7165940363836563642[7] = 0;
   out_7165940363836563642[8] = 0;
   out_7165940363836563642[9] = 0;
   out_7165940363836563642[10] = 0;
   out_7165940363836563642[11] = 0;
   out_7165940363836563642[12] = 0;
   out_7165940363836563642[13] = 0;
   out_7165940363836563642[14] = 0;
   out_7165940363836563642[15] = 0;
   out_7165940363836563642[16] = 0;
   out_7165940363836563642[17] = 0;
   out_7165940363836563642[18] = 0;
   out_7165940363836563642[19] = 0;
   out_7165940363836563642[20] = 0;
   out_7165940363836563642[21] = 0;
   out_7165940363836563642[22] = 1;
   out_7165940363836563642[23] = 0;
   out_7165940363836563642[24] = 0;
   out_7165940363836563642[25] = 0;
   out_7165940363836563642[26] = 0;
   out_7165940363836563642[27] = 0;
   out_7165940363836563642[28] = 0;
   out_7165940363836563642[29] = 0;
   out_7165940363836563642[30] = 0;
   out_7165940363836563642[31] = 0;
   out_7165940363836563642[32] = 0;
   out_7165940363836563642[33] = 0;
   out_7165940363836563642[34] = 0;
   out_7165940363836563642[35] = 0;
   out_7165940363836563642[36] = 0;
   out_7165940363836563642[37] = 0;
   out_7165940363836563642[38] = 0;
   out_7165940363836563642[39] = 0;
   out_7165940363836563642[40] = 0;
   out_7165940363836563642[41] = 1;
   out_7165940363836563642[42] = 0;
   out_7165940363836563642[43] = 0;
   out_7165940363836563642[44] = 0;
   out_7165940363836563642[45] = 0;
   out_7165940363836563642[46] = 0;
   out_7165940363836563642[47] = 0;
   out_7165940363836563642[48] = 0;
   out_7165940363836563642[49] = 0;
   out_7165940363836563642[50] = 0;
   out_7165940363836563642[51] = 0;
   out_7165940363836563642[52] = 0;
   out_7165940363836563642[53] = 0;
}
void h_14(double *state, double *unused, double *out_5129805537420960347) {
   out_5129805537420960347[0] = state[6];
   out_5129805537420960347[1] = state[7];
   out_5129805537420960347[2] = state[8];
}
void H_14(double *state, double *unused, double *out_4985741452245282877) {
   out_4985741452245282877[0] = 0;
   out_4985741452245282877[1] = 0;
   out_4985741452245282877[2] = 0;
   out_4985741452245282877[3] = 0;
   out_4985741452245282877[4] = 0;
   out_4985741452245282877[5] = 0;
   out_4985741452245282877[6] = 1;
   out_4985741452245282877[7] = 0;
   out_4985741452245282877[8] = 0;
   out_4985741452245282877[9] = 0;
   out_4985741452245282877[10] = 0;
   out_4985741452245282877[11] = 0;
   out_4985741452245282877[12] = 0;
   out_4985741452245282877[13] = 0;
   out_4985741452245282877[14] = 0;
   out_4985741452245282877[15] = 0;
   out_4985741452245282877[16] = 0;
   out_4985741452245282877[17] = 0;
   out_4985741452245282877[18] = 0;
   out_4985741452245282877[19] = 0;
   out_4985741452245282877[20] = 0;
   out_4985741452245282877[21] = 0;
   out_4985741452245282877[22] = 0;
   out_4985741452245282877[23] = 0;
   out_4985741452245282877[24] = 0;
   out_4985741452245282877[25] = 1;
   out_4985741452245282877[26] = 0;
   out_4985741452245282877[27] = 0;
   out_4985741452245282877[28] = 0;
   out_4985741452245282877[29] = 0;
   out_4985741452245282877[30] = 0;
   out_4985741452245282877[31] = 0;
   out_4985741452245282877[32] = 0;
   out_4985741452245282877[33] = 0;
   out_4985741452245282877[34] = 0;
   out_4985741452245282877[35] = 0;
   out_4985741452245282877[36] = 0;
   out_4985741452245282877[37] = 0;
   out_4985741452245282877[38] = 0;
   out_4985741452245282877[39] = 0;
   out_4985741452245282877[40] = 0;
   out_4985741452245282877[41] = 0;
   out_4985741452245282877[42] = 0;
   out_4985741452245282877[43] = 0;
   out_4985741452245282877[44] = 1;
   out_4985741452245282877[45] = 0;
   out_4985741452245282877[46] = 0;
   out_4985741452245282877[47] = 0;
   out_4985741452245282877[48] = 0;
   out_4985741452245282877[49] = 0;
   out_4985741452245282877[50] = 0;
   out_4985741452245282877[51] = 0;
   out_4985741452245282877[52] = 0;
   out_4985741452245282877[53] = 0;
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
void pose_err_fun(double *nom_x, double *delta_x, double *out_731387772078245243) {
  err_fun(nom_x, delta_x, out_731387772078245243);
}
void pose_inv_err_fun(double *nom_x, double *true_x, double *out_4206130707332622452) {
  inv_err_fun(nom_x, true_x, out_4206130707332622452);
}
void pose_H_mod_fun(double *state, double *out_2916011499501574438) {
  H_mod_fun(state, out_2916011499501574438);
}
void pose_f_fun(double *state, double dt, double *out_4420889553799640425) {
  f_fun(state,  dt, out_4420889553799640425);
}
void pose_F_fun(double *state, double dt, double *out_586752082486093199) {
  F_fun(state,  dt, out_586752082486093199);
}
void pose_h_4(double *state, double *unused, double *out_1330626957984611772) {
  h_4(state, unused, out_1330626957984611772);
}
void pose_H_4(double *state, double *unused, double *out_8068529884540655173) {
  H_4(state, unused, out_8068529884540655173);
}
void pose_h_10(double *state, double *unused, double *out_5440536108172962293) {
  h_10(state, unused, out_5440536108172962293);
}
void pose_H_10(double *state, double *unused, double *out_3777395375513848052) {
  H_10(state, unused, out_3777395375513848052);
}
void pose_h_13(double *state, double *unused, double *out_7911476404081815631) {
  h_13(state, unused, out_7911476404081815631);
}
void pose_H_13(double *state, double *unused, double *out_7165940363836563642) {
  H_13(state, unused, out_7165940363836563642);
}
void pose_h_14(double *state, double *unused, double *out_5129805537420960347) {
  h_14(state, unused, out_5129805537420960347);
}
void pose_H_14(double *state, double *unused, double *out_4985741452245282877) {
  H_14(state, unused, out_4985741452245282877);
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
